#!/usr/bin/env python3
"""A self-consistent package must still contain the exact strength-tested binary."""
from __future__ import annotations

import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
sys.path.insert(0, str(ROOT / "release"))
from create_validation_notes import PRIOR_REPORT_PATH, validate_evidence, verification_notes
from paired_match_gate import markdown_report, paired_statistics
from run_paired_validation import REPLICATION_BUILD_RUN, REPLICATION_PROTOCOL, REPLICATION_SOURCE
from verify_release_assets import STRENGTH_PLATFORM, digest, verify_strength_identity


class ReleaseIdentityTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.path = Path(self.temporary.name) / "linux-pgo.zip"
        self.commit = "a" * 40
        self.tested_binary = b"strength-tested Linux AVX2 PGO executable fixture"
        self.report = {
            "valid": True, "approved": True, "mode": "confirmation",
            "candidate_sha": self.commit, "candidate_build_profile": "pgo-avx2",
            "candidate_binary_sha256": digest(self.tested_binary),
        }
        self.write_package(self.tested_binary)

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def write_package(self, binary: bytes, **overrides: str) -> None:
        manifest = {
            "platform": STRENGTH_PLATFORM, "build_profile": "pgo",
            "source_commit": self.commit, "binary": "stockless",
            "binary_sha256": digest(binary),
            **overrides,
        }
        with zipfile.ZipFile(self.path, "w") as archive:
            archive.writestr("stockless", binary)
            archive.writestr("manifest.json", json.dumps(manifest))

    def test_approved_report_accepts_identical_executable_bytes(self) -> None:
        verify_strength_identity(self.path, self.report, self.commit)

    def test_self_consistent_rebuilt_binary_is_rejected(self) -> None:
        # Updating BOTH binary and manifest passes an ordinary archive checksum
        # check. It must not inherit the original binary's strength evidence.
        self.write_package(b"different rebuild with its own valid checksum")
        with self.assertRaisesRegex(RuntimeError, "differs from the strength-tested bytes"):
            verify_strength_identity(self.path, self.report, self.commit)

    def test_matching_manifest_cannot_hide_swapped_executable(self) -> None:
        self.write_package(b"swapped executable", binary_sha256=digest(self.tested_binary))
        with self.assertRaisesRegex(RuntimeError, "differs from the strength-tested bytes"):
            verify_strength_identity(self.path, self.report, self.commit)

    def test_report_and_package_must_both_match_expected_source(self) -> None:
        report = {**self.report, "candidate_sha": "b" * 40}
        with self.assertRaisesRegex(RuntimeError, "expected source"):
            verify_strength_identity(self.path, report, self.commit)
        self.write_package(self.tested_binary, source_commit="b" * 40)
        with self.assertRaisesRegex(RuntimeError, "source commit"):
            verify_strength_identity(self.path, self.report, self.commit)
        with self.assertRaisesRegex(RuntimeError, "requires --expected-commit"):
            verify_strength_identity(self.path, self.report, None)

    def test_failed_exploratory_or_non_pgo_evidence_cannot_publish(self) -> None:
        for changes in ({"approved": False}, {"valid": False}, {"mode": "exploratory"},
                        {"candidate_build_profile": "standard-avx2"}):
            with self.subTest(changes=changes), self.assertRaisesRegex(RuntimeError, "not approved PGO"):
                verify_strength_identity(self.path, {**self.report, **changes}, self.commit)
        self.write_package(self.tested_binary, build_profile="standard-compatibility")
        with self.assertRaisesRegex(RuntimeError, "wrong platform, profile"):
            verify_strength_identity(self.path, self.report, self.commit)


class ReplicationReleasePolicyTests(unittest.TestCase):
    """A later workflow may publish only the frozen, explicitly confirmed experiment."""

    def setUp(self) -> None:
        self.prior = json.loads(PRIOR_REPORT_PATH.read_text())
        self.report = copy.deepcopy(self.prior)
        self.orchestrator = "e" * 40
        self.report.update({
            "approved": True, "protocol_id": REPLICATION_PROTOCOL,
            "orchestrator_sha": self.orchestrator, "prior_run_id": REPLICATION_BUILD_RUN,
            "build_run_id": REPLICATION_BUILD_RUN, "unique_openings": 6144,
        })
        short = self.report["stages"][0]
        short["confidence_level"] = 0.95
        short["statistics"].update({
            "confidence_level": 0.95,
            "score_ci": short["statistics"]["score_ci95"],
            "elo_ci": short["statistics"]["elo_ci95"],
        })
        longer = self.report["stages"][1]
        longer.update({
            "name": "long-final", "minimum_games": 8192,
            "confidence_level": 0.99, "passed": True,
            "statistics": paired_statistics([1.0, 0.5] * 768 + [0.5, 0.5] * 3072
                                             + [0.0, 0.5] * 256, confidence_level=0.99),
        })

    def validate(self) -> None:
        validate_evidence(self.report, REPLICATION_SOURCE, self.orchestrator, self.prior)

    def test_frozen_replication_and_unchanged_prior_are_accepted(self) -> None:
        self.validate()

    def test_missing_or_modified_prior_cannot_erase_the_inconclusive_result(self) -> None:
        with self.assertRaisesRegex(RuntimeError, "requires the original inconclusive"):
            validate_evidence(self.report, REPLICATION_SOURCE, self.orchestrator)
        self.prior["approved"] = True
        with self.assertRaisesRegex(RuntimeError, "differs from the preserved"):
            self.validate()

    def test_exact_source_hashes_and_provenance_are_required(self) -> None:
        for key, value in (("candidate_sha", "b" * 40),
                           ("candidate_binary_sha256", "b" * 64),
                           ("baseline_binary_sha256", "b" * 64),
                           ("orchestrator_sha", "b" * 40),
                           ("prior_run_id", 1), ("build_run_id", 1)):
            with self.subTest(key=key):
                changed = {**self.report, key: value}
                with self.assertRaises(RuntimeError):
                    validate_evidence(changed, REPLICATION_SOURCE, self.orchestrator, self.prior)

    def test_selected_99_interval_must_pass_even_when_95_interval_passes(self) -> None:
        stats = self.report["stages"][1]["statistics"]
        self.assertGreater(stats["score_ci95"][0], 0.5)
        stats["score_ci"] = [0.499, stats["score_ci"][1]]
        with self.assertRaisesRegex(RuntimeError, "insufficient predeclared long-final"):
            self.validate()

    def test_95_interval_cannot_be_relabelled_as_99(self) -> None:
        stage = self.report["stages"][1]
        stage["confidence_level"] = 0.95
        stage["statistics"]["confidence_level"] = 0.95
        with self.assertRaisesRegex(RuntimeError, "insufficient predeclared long-final"):
            self.validate()
        stage["confidence_level"] = stage["statistics"]["confidence_level"] = 0.99
        del stage["statistics"]["score_ci"]
        with self.assertRaisesRegex(RuntimeError, "insufficient predeclared long-final"):
            self.validate()

    def test_reused_short_statistics_and_all_four_file_hashes_are_unchanged(self) -> None:
        original = copy.deepcopy(self.report)
        self.report["stages"][0]["statistics"]["wins"] += 1
        with self.assertRaisesRegex(RuntimeError, "Reused short statistics differ"):
            self.validate()
        for filename in ("match.pgn", "match.log", "openings.epd", "metadata.json"):
            self.report = copy.deepcopy(original)
            self.report["stages"][0]["shards"][0]["files_sha256"][filename] = "b" * 64
            with self.subTest(filename=filename), self.assertRaisesRegex(RuntimeError, "Reused short evidence files differ"):
                self.validate()

    def test_sample_size_stage_names_and_thresholds_are_fixed(self) -> None:
        original = copy.deepcopy(self.report)
        for change in ("games", "threshold", "opening_count", "extra_stage", "unknown_protocol"):
            self.report = copy.deepcopy(original)
            if change == "games":
                self.report["stages"][1]["statistics"]["games"] = 8190
            elif change == "threshold":
                self.report["stages"][0]["min_elo"] = 0
            elif change == "opening_count":
                self.report["unique_openings"] = 6143
            elif change == "extra_stage":
                self.report["stages"].append(copy.deepcopy(self.report["stages"][1]))
            else:
                self.report["protocol_id"] = "unplanned-follow-up"
            with self.subTest(change=change), self.assertRaises(RuntimeError):
                self.validate()

    def test_original_protocol_stays_bound_to_current_source_and_old_counts(self) -> None:
        report = copy.deepcopy(self.prior)
        report["approved"] = True
        report["stages"][1]["passed"] = True
        report["stages"][1]["statistics"] = paired_statistics([1.0, 0.5] * 384 + [0.5, 0.5] * 128)
        validate_evidence(report, REPLICATION_SOURCE, REPLICATION_SOURCE)
        with self.assertRaisesRegex(RuntimeError, "cannot override the current source"):
            validate_evidence(report, REPLICATION_SOURCE, self.orchestrator)
        report["stages"][1]["statistics"]["games"] = 8192
        with self.assertRaisesRegex(RuntimeError, "insufficient predeclared long"):
            validate_evidence(report, REPLICATION_SOURCE, REPLICATION_SOURCE)

    def test_notes_disclose_both_experiments_and_distinct_source_commits(self) -> None:
        self.validate()
        notes = verification_notes(self.report, markdown_report(self.report), REPLICATION_SOURCE,
                                   self.orchestrator, 12345, self.prior)
        for required in (REPLICATION_SOURCE, self.orchestrator, str(REPLICATION_BUILD_RUN),
                         "Release approved: **False**", "Release approved: **True**",
                         "8,192 new games", "99%", "unchanged original sample",
                         "prior-report.json", "five standard universal/compatibility packages"):
            with self.subTest(required=required):
                self.assertIn(required, notes)


if __name__ == "__main__":
    unittest.main()
