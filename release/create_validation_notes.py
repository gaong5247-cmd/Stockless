#!/usr/bin/env python3
"""Generate release notes only from complete, approved fixed-source evidence."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from package_release import read_version
from paired_match_gate import markdown_report
from run_paired_validation import BASELINE_SHA


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--summary", type=Path, required=True)
    parser.add_argument("--source-sha", required=True)
    parser.add_argument("--run-id", type=int, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    report = json.loads(args.report.read_text())
    if not (report.get("valid") is True and report.get("approved") is True
            and report.get("mode") == "confirmation"
            and report.get("candidate_build_profile") == "pgo-avx2"
            and report.get("baseline_build_profile") == "standard-avx2"
            and report.get("candidate_sha") == args.source_sha
            and report.get("baseline_sha") == BASELINE_SHA):
        raise RuntimeError("Release requires approved confirmation for this exact candidate and baseline")
    stages = {stage["name"]: stage for stage in report["stages"]}
    for name, games, tc, min_elo in [("short", 4096, "2+0.02", 5), ("long", 1024, "5+0.05", 0)]:
        stage = stages.get(name, {})
        stats = stage.get("statistics", {})
        if not (stage.get("passed") is True and stage.get("time_control") == tc
                and stats.get("games") == games and stats.get("pairs") == games // 2
                and stats["score_ci95"][0] > 0.5
                and (stats["elo"] == "+inf" or stats["elo"] >= min_elo)):
            raise RuntimeError(f"Missing or insufficient predeclared {name} confirmation")
    if len(stages) != 2 or report.get("unique_openings") != 2560:
        raise RuntimeError("Unexpected confirmation stages or opening count")
    summary = markdown_report(report)
    if args.summary.read_text() != summary:
        raise RuntimeError("Human-readable evidence differs from the machine-readable report")
    notes = (ROOT / "docs/RELEASE_v0.9.0.md").read_text()
    notes += f"\n## Completed verification\n\nSource: `{args.source_sha}`. "
    notes += f"[Actions run](https://github.com/gaong5247-cmd/Stockless/actions/runs/{args.run_id}).\n\n"
    notes += summary.replace("# Stockless paired strength gate", "### Independent paired matches", 1)
    args.output.write_text(notes)
    print(f"Approved release notes created for {read_version()}, source {args.source_sha}")


if __name__ == "__main__":
    main()
