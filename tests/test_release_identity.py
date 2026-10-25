#!/usr/bin/env python3
"""A self-consistent package must still contain the exact strength-tested binary."""
from __future__ import annotations

import json
from pathlib import Path
import sys
import tempfile
import unittest
import zipfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
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


if __name__ == "__main__":
    unittest.main()
