#!/usr/bin/env python3
"""Verify the original artifacts before the single, frozen longer-TC follow-up."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import shutil

from run_paired_validation import (
    BASELINE_SHA, REPLICATION_BASELINE_HASH, REPLICATION_BUILD_RUN,
    REPLICATION_CANDIDATE_HASH, REPLICATION_POOL_HASH, REPLICATION_PROTOCOL,
    REPLICATION_SOURCE, STAGES, digest,
)

ROOT = Path(__file__).resolve().parents[1]


def prepare(build: Path, prior: Path, output: Path) -> None:
    archived = json.loads((ROOT / "docs/validation/v0.9.0-pgo-20261025.json").read_text())
    report_path = prior / "validation-report/report.json"
    report = json.loads(report_path.read_text())
    if report != archived:
        raise RuntimeError("Original report differs from the preserved, rejected experiment")
    if not (report["valid"] is True and report["approved"] is False
            and report["candidate_sha"] == REPLICATION_SOURCE
            and report["baseline_sha"] == BASELINE_SHA
            and report["candidate_binary_sha256"] == REPLICATION_CANDIDATE_HASH
            and report["baseline_binary_sha256"] == REPLICATION_BASELINE_HASH):
        raise RuntimeError("Unexpected original experiment or binary identities")
    if (build / "candidate-sha.txt").read_text().strip() != REPLICATION_SOURCE:
        raise RuntimeError("Downloaded build has the wrong source revision")
    for name, expected in (("candidate", REPLICATION_CANDIDATE_HASH),
                           ("baseline", REPLICATION_BASELINE_HASH),
                           ("openings.epd", REPLICATION_POOL_HASH)):
        if digest(build / name) != expected:
            raise RuntimeError(f"Downloaded {name} differs from the frozen artifact")
    stages = {stage["name"]: stage for stage in report["stages"]}
    short, previous_long = stages["short"], stages["long"]
    if not (short["passed"] is True and short["statistics"]["games"] == 4096
            and previous_long["passed"] is False
            and previous_long["statistics"]["games"] == 1024):
        raise RuntimeError("The follow-up is only for the recorded inconclusive longer stage")
    pool = (build / "openings.epd").read_text().splitlines()
    games, count, _, offset = STAGES["long-final"]
    if len(pool) < offset + games * count // 2:
        raise RuntimeError("Frozen opening pool is too short")
    if output.exists() and any(output.iterdir()):
        raise RuntimeError("Refusing to mix new evidence with an existing results directory")
    output.mkdir(parents=True, exist_ok=True)
    for shard in short["shards"]:
        name = Path(shard["directory"]).name
        source = prior / "results" / name
        for filename, expected in shard["files_sha256"].items():
            if Path(filename).name != filename or digest(source / filename) != expected:
                raise RuntimeError(f"Original short evidence changed: {name}/{filename}")
        index = int(name.removeprefix("short-"))
        short_games, short_count, _, short_offset = STAGES["short"]
        if not (0 <= index < short_count):
            raise RuntimeError("Unexpected original short shard")
        start = short_offset + index * short_games // 2
        expected_openings = pool[start:start + short_games // 2]
        if (source / "openings.epd").read_text().splitlines() != expected_openings:
            raise RuntimeError("Original short positions differ from the frozen opening allocation")
        shutil.copytree(source, output / name)
    if len(list(output.iterdir())) != 8:
        raise RuntimeError("Expected all eight original short shards")
    print(json.dumps({
        "protocol_id": REPLICATION_PROTOCOL,
        "engine_source_sha": REPLICATION_SOURCE,
        "build_run_id": REPLICATION_BUILD_RUN,
        "candidate_binary_sha256": REPLICATION_CANDIDATE_HASH,
        "baseline_binary_sha256": REPLICATION_BASELINE_HASH,
        "reused_short_games": 4096,
        "new_long_games": 8192,
        "new_long_opening_range": [offset, offset + games * count // 2 - 1],
        "new_long_confidence": 0.99,
        "previous_long_games_pooled": 0,
        "further_attempts_permitted": False,
    }, indent=2))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--build", type=Path, required=True)
    parser.add_argument("--prior-evidence", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    prepare(args.build, args.prior_evidence, args.output)


if __name__ == "__main__":
    main()
