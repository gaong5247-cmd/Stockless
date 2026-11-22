#!/usr/bin/env python3
"""Gate a maintenance release on unchanged generated engine sources.

This path cannot approve changed search, evaluation, defaults, upstream pins,
or build flags. Those changes need a separately declared strength experiment.
Only the UCI version string may differ in the generated src/ tree. Runtime
bench fingerprints and platform smoke tests are additional workflow gates.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess

ROOT = Path(__file__).resolve().parents[1]
VERSION = re.compile(rb'(inline constexpr const char\* Version = ")v\d+\.\d+\.\d+(";)')


def git(root: Path, *args: str) -> str:
    return subprocess.check_output(["git", "-C", str(root), *args], text=True).strip()


def source_snapshot(directory: Path) -> dict[str, str]:
    """Fingerprint a freshly materialized tree, before compilation/downloads."""
    if not directory.is_dir():
        raise RuntimeError(f"Missing source directory: {directory}")
    result = {}
    for path in sorted(directory.rglob("*")):
        if path.is_symlink():
            raise RuntimeError(f"Unexpected source symlink: {path}")
        if not path.is_file():
            continue
        name = path.relative_to(directory).as_posix()
        data = path.read_bytes()
        if name in ("config.h", "stockless_core/config.h"):
            data, count = VERSION.subn(rb'\1<release-version>\2', data)
            if count != 1:
                raise RuntimeError(f"Expected exactly one UCI version in {path}")
        result[name] = hashlib.sha256(data).hexdigest()
    if not result:
        raise RuntimeError(f"Empty source directory: {directory}")
    return result


def compare_sources(baseline: Path, candidate: Path) -> int:
    before, after = source_snapshot(baseline), source_snapshot(candidate)
    different = sorted(name for name in before.keys() | after.keys()
                       if before.get(name) != after.get(name))
    if different:
        raise RuntimeError("Maintenance release changes engine sources: " + ", ".join(different)
                           + ". Use independent strength validation for engine changes.")
    return len(after)


def read_version(root: Path) -> str:
    match = VERSION.search((root / "src/stockless/config.h").read_bytes())
    if match is None:
        raise RuntimeError("Missing stable semantic version")
    return match.group(0).split(b'"')[1].decode("ascii")


def verify_plan(plan: dict, baseline_version: str, candidate_version: str) -> None:
    if plan.get("schema") != 1 or plan.get("kind") != "maintenance":
        raise RuntimeError("Expected a schema-1 maintenance plan")
    if plan.get("playing_strength_claim") is not False:
        raise RuntimeError("Maintenance publication cannot assert a playing-strength gain")
    expected = tuple(int(n) for n in baseline_version[1:].split("."))
    actual = tuple(int(n) for n in candidate_version[1:].split("."))
    if actual != (expected[0], expected[1], expected[2] + 1):
        raise RuntimeError("Maintenance version must be the next patch of the baseline")
    if plan.get("version") != candidate_version or plan.get("tag") != "Stockless_" + candidate_version:
        raise RuntimeError("Maintenance plan version/tag mismatch")
    if plan.get("baseline_tag") != "Stockless_" + baseline_version:
        raise RuntimeError("Baseline tag/version mismatch")
    if not re.fullmatch(r"[0-9a-f]{40}", plan.get("baseline_commit", "")):
        raise RuntimeError("Baseline must be an exact commit")
    if plan.get("notes") != f"docs/RELEASE_{candidate_version}.md":
        raise RuntimeError("Expected version-specific release notes")


def verify(baseline: Path, candidate: Path, expected_commit: str) -> dict:
    plan = json.loads((candidate / "release/maintenance.json").read_text(encoding="utf-8"))
    version, baseline_version = read_version(candidate), read_version(baseline)
    verify_plan(plan, baseline_version, version)
    if not re.fullmatch(r"[0-9a-f]{40}", expected_commit):
        raise RuntimeError("Candidate must be an exact commit")
    if git(candidate, "rev-parse", "HEAD") != expected_commit:
        raise RuntimeError("Candidate checkout differs from expected commit")
    if git(baseline, "rev-parse", "HEAD") != plan["baseline_commit"]:
        raise RuntimeError("Baseline checkout differs from frozen release commit")
    if git(candidate, "rev-parse", plan["baseline_tag"] + "^{commit}") != plan["baseline_commit"]:
        raise RuntimeError("Baseline tag does not resolve to the frozen release commit")
    # HEAD alone does not rule out uncommitted input changes.
    for root in (baseline, candidate):
        if git(root, "status", "--porcelain", "--untracked-files=no"):
            raise RuntimeError(f"Tracked source changes in {root}")
    pins = {}
    for name in ("stockfish", "reckless"):
        path = f"upstream/{name}"
        before = git(baseline, "ls-tree", "HEAD", path)
        after = git(candidate, "ls-tree", "HEAD", path)
        if before != after or not after.startswith("160000 commit "):
            raise RuntimeError(f"Changed upstream pin: {name}")
        pin = after.split()[2]
        for root in (baseline, candidate):
            if git(root / path, "rev-parse", "HEAD") != pin:
                raise RuntimeError(f"Submodule checkout differs from pin: {root / path}")
        pins[name] = pin
    overlay_count = compare_sources(baseline / "src/stockless", candidate / "src/stockless")
    source_count = compare_sources(baseline / "build/stockless-src/src",
                                   candidate / "build/stockless-src/src")
    # PGO flags/training remain the established v0.9.0 procedure.
    if (baseline / "scripts/build-pgo.sh").read_bytes() != (candidate / "scripts/build-pgo.sh").read_bytes():
        raise RuntimeError("Maintenance release changes the PGO build procedure")
    if not (candidate / plan["notes"]).is_file():
        raise RuntimeError("Missing release notes")
    return {"schema": 1, "kind": "maintenance", "version": version, "tag": plan["tag"],
            "baseline_commit": plan["baseline_commit"], "candidate_commit": expected_commit,
            "runtime_source_equivalent": True, "playing_strength_claim": False,
            "overlay_files": overlay_count, "generated_source_files": source_count,
            "upstream_pins": pins,
            "scope": "Source equivalence with only UCI version changed; no new Elo estimate."}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline", required=True, type=Path)
    parser.add_argument("--candidate", type=Path, default=ROOT)
    parser.add_argument("--expected-commit", required=True)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    report = verify(args.baseline.resolve(), args.candidate.resolve(), args.expected_commit)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
