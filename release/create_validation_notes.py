#!/usr/bin/env python3
"""Generate release notes only from complete, approved fixed-source evidence."""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from package_release import read_version
from paired_match_gate import markdown_report
from run_paired_validation import (
    BASELINE_SHA, REPLICATION_BASELINE_HASH, REPLICATION_BUILD_RUN,
    REPLICATION_CANDIDATE_HASH, REPLICATION_PROTOCOL, REPLICATION_SOURCE,
)

PRIOR_REPORT_PATH = ROOT / "docs/validation/v0.9.0-pgo-20261025.json"


def stage_map(report: dict) -> dict[str, dict]:
    stages = report.get("stages", [])
    if not isinstance(stages, list) or not all(isinstance(stage, dict) for stage in stages):
        raise RuntimeError("Invalid confirmation stages")
    names = [stage.get("name") for stage in stages]
    if not all(isinstance(name, str) for name in names) or len(names) != len(set(names)):
        raise RuntimeError("Confirmation stage names must be unique")
    return dict(zip(names, stages))


def validate_stage(stage: dict, name: str, games: int, tc: str, min_elo: float,
                   confidence: float, *, selected_required: bool) -> None:
    stats = stage.get("statistics", {})
    score_ci = stats.get("score_ci", stats.get("score_ci95"))
    elo = stats.get("elo")
    sufficient_elo = (elo == "+inf" or
                      (type(elo) in (int, float) and math.isfinite(elo) and elo >= min_elo))
    positive_ci = (isinstance(score_ci, list) and len(score_ci) == 2
                   and all(type(value) in (int, float) and math.isfinite(value) for value in score_ci)
                   and 0.5 < score_ci[0] <= score_ci[1] <= 1.0)
    selected_present = ("score_ci" in stats and "elo_ci" in stats
                        and stage.get("confidence_level") == confidence
                        and stats.get("confidence_level") == confidence)
    if not (stage.get("passed") is True and stage.get("time_control") == tc
            and stage.get("minimum_games") == games and stage.get("min_elo") == min_elo
            and stats.get("games") == games and stats.get("pairs") == games // 2
            and stage.get("confidence_level", 0.95) == confidence
            and stats.get("confidence_level", 0.95) == confidence
            and (not selected_required or selected_present)
            and positive_ci and sufficient_elo):
        raise RuntimeError(f"Missing or insufficient predeclared {name} confirmation")


def shard_fingerprints(stage: dict) -> list[str]:
    """Artifact paths may move; every recorded evidence file must retain its bytes."""
    shards = stage.get("shards", [])
    if len(shards) != 8 or any(set(shard.get("files_sha256", {})) != {
            "match.pgn", "match.log", "openings.epd", "metadata.json"} for shard in shards):
        raise RuntimeError("Expected all eight original short evidence shards")
    return sorted(json.dumps(shard["files_sha256"], sort_keys=True) for shard in shards)


def validate_evidence(report: dict, source_sha: str, orchestrator_sha: str,
                      prior_report: dict | None = None) -> None:
    if not all(re.fullmatch(r"[0-9a-f]{40}", sha) for sha in (source_sha, orchestrator_sha)):
        raise RuntimeError("Engine source and orchestration commits must be full Git SHAs")
    if not (report.get("valid") is True and report.get("approved") is True
            and report.get("mode") == "confirmation"
            and report.get("candidate_build_profile") == "pgo-avx2"
            and report.get("baseline_build_profile") == "standard-avx2"
            and report.get("candidate_sha") == source_sha
            and report.get("baseline_sha") == BASELINE_SHA):
        raise RuntimeError("Release requires approved confirmation for this exact candidate and baseline")
    stages = stage_map(report)
    protocol = report.get("protocol_id")
    if protocol in (None, ""):
        if source_sha != orchestrator_sha:
            raise RuntimeError("The original protocol cannot override the current source commit")
        if prior_report is not None:
            raise RuntimeError("Prior evidence requires the declared replication protocol")
        requirements = [("short", 4096, "2+0.02", 5, 0.95),
                        ("long", 1024, "5+0.05", 0, 0.95)]
        openings = 2560
    elif protocol == REPLICATION_PROTOCOL:
        if not (source_sha == REPLICATION_SOURCE
                and report.get("candidate_binary_sha256") == REPLICATION_CANDIDATE_HASH
                and report.get("baseline_binary_sha256") == REPLICATION_BASELINE_HASH
                and report.get("orchestrator_sha") == orchestrator_sha
                and report.get("prior_run_id") == REPLICATION_BUILD_RUN
                and report.get("build_run_id") == REPLICATION_BUILD_RUN):
            raise RuntimeError("Replication requires the exact frozen binaries and recorded provenance")
        if prior_report is None:
            raise RuntimeError("Replication requires the original inconclusive prior report")
        archived = json.loads(PRIOR_REPORT_PATH.read_text())
        if prior_report != archived:
            raise RuntimeError("Prior report differs from the preserved original experiment")
        identity_keys = ("candidate_sha", "baseline_sha", "candidate_build_profile",
                         "baseline_build_profile", "candidate_binary_sha256", "baseline_binary_sha256")
        if not (prior_report.get("valid") is True and prior_report.get("approved") is False
                and prior_report.get("mode") == "confirmation"
                and all(prior_report.get(key) == report.get(key) for key in identity_keys)):
            raise RuntimeError("Prior report must preserve the same valid, unapproved experiment")
        original_short = stage_map(prior_report)["short"]
        repeated_short = stages.get("short", {})
        original_stats = original_short["statistics"]
        repeated_stats = repeated_short.get("statistics", {})
        if any(repeated_stats.get(key) != value for key, value in original_stats.items() if key != "method"):
            raise RuntimeError("Reused short statistics differ from the original experiment")
        if shard_fingerprints(original_short) != shard_fingerprints(repeated_short):
            raise RuntimeError("Reused short evidence files differ from the original experiment")
        requirements = [("short", 4096, "2+0.02", 5, 0.95),
                        ("long-final", 8192, "5+0.05", 0, 0.99)]
        openings = 6144
    else:
        raise RuntimeError("Unknown release validation protocol")
    if set(stages) != {requirement[0] for requirement in requirements} or report.get("unique_openings") != openings:
        raise RuntimeError("Unexpected confirmation stages or opening count")
    for name, games, tc, min_elo, confidence in requirements:
        validate_stage(stages[name], name, games, tc, min_elo, confidence,
                       selected_required=protocol == REPLICATION_PROTOCOL)


def verification_notes(report: dict, summary: str, source_sha: str, orchestrator_sha: str,
                       run_id: int, prior_report: dict | None) -> str:
    notes = (ROOT / "docs/RELEASE_v0.9.0.md").read_text()
    notes += "\n## Completed verification\n\n"
    notes += f"Engine source: `{source_sha}`. Release orchestration: `{orchestrator_sha}`. "
    notes += f"[Publication Actions run](https://github.com/gaong5247-cmd/Stockless/actions/runs/{run_id}).\n\n"
    if report.get("protocol_id") == REPLICATION_PROTOCOL:
        notes += (
            "### Original experiment, preserved unchanged\n\n"
            f"[Original Actions run](https://github.com/gaong5247-cmd/Stockless/actions/runs/{REPLICATION_BUILD_RUN}) "
            "completed 4,096 short and 1,024 longer-time-control games. Its longer stage was "
            "inconclusive, so that experiment did not approve a release. The original report is "
            "preserved as the `prior-report.json` release asset with its approval status unchanged.\n\n"
        )
        notes += markdown_report(prior_report).replace("# Stockless paired strength gate", "#### Original result", 1)
        notes += (
            "\n### One bounded independent follow-up\n\n"
            f"Protocol `{REPLICATION_PROTOCOL}` reused the identical Linux candidate and baseline "
            "executables. It completed a fixed sample of 8,192 new games at `5+0.05` on 4,096 fresh, "
            "color-reversed opening pairs, using a two-sided 99% pair-level confidence interval. "
            "The source and engine settings stayed frozen, and this protocol permits one follow-up. "
            "The original 1,024 longer games remain in the archived experiment and are excluded "
            "from the new 8,192-game estimate. The 4,096 short games shown again below are the "
            "unchanged original sample; they were not played a second time.\n\n"
        )
    notes += summary.replace("# Stockless paired strength gate", "### Release evidence", 1)
    notes += (
        "\n### Scope of the measured improvement\n\n"
        "The evidence supports a modest improvement for the exact Linux x86-64 AVX2 PGO executable "
        "against the frozen v0.8.9 baseline under these time controls, options and runner conditions. "
        "That executable is packaged without rebuilding. The Windows AVX2 PGO package is a separately "
        "compiled companion checked for matching same-source search behavior. Its playing strength "
        "has not been independently measured. The five standard universal/compatibility packages "
        "provide platform coverage and do not inherit the Linux PGO strength estimate.\n"
    )
    return notes


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--summary", type=Path, required=True)
    parser.add_argument("--source-sha", required=True)
    parser.add_argument("--orchestrator-sha", required=True)
    parser.add_argument("--run-id", type=int, required=True)
    parser.add_argument("--prior-report", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.run_id <= 0:
        raise RuntimeError("Actions run ID must be positive")
    report = json.loads(args.report.read_text())
    prior = json.loads(args.prior_report.read_text()) if args.prior_report else None
    validate_evidence(report, args.source_sha, args.orchestrator_sha, prior)
    summary = markdown_report(report)
    if args.summary.read_text() != summary:
        raise RuntimeError("Human-readable evidence differs from the machine-readable report")
    args.output.write_text(verification_notes(report, summary, args.source_sha, args.orchestrator_sha,
                                             args.run_id, prior))
    print(f"Approved release notes created for {read_version()}, source {args.source_sha}")


if __name__ == "__main__":
    main()
