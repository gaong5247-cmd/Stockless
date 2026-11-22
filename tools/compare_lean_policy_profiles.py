#!/usr/bin/env python3
"""Ensure refactored policy preserves bench searches under multiple UCI modes.

Compare binaries compiled with the same Stockfish, NNUE, CPU ISA and flags.
The per-profile node-count and bestmove signatures must agree exactly.
This is a correctness gate, NOT an Elo or speed claim.
"""
from __future__ import annotations

import argparse
import subprocess
from pathlib import Path

from bench_output import BenchResult, default_bench_position_count, parse_bench

# Cover every supported lean Stockless mode; retired history options must not be sent.
# Include mobile+Overdrive to cover the mobile restriction.
PROFILES = {
    "stockless-default": {},
    "hybrid-off": {"StocklessHybrid": "false"},
    "threats-off": {"StocklessThreats": "false"},
    "aggression-zero": {"StocklessAggression": "0"},
    "aggression-max": {"StocklessAggression": "200"},
    "overdrive-desktop": {"StocklessOverdrive": "true"},
    "overdrive-mobile": {"StocklessOverdrive": "true", "StocklessMobile": "true"},
    "mobile-default": {"StocklessMobile": "true"},
}

DEFAULT_OPTIONS = {
    "Threads": "1",
    "Hash": "16",
    "StocklessHybrid": "true",
    "StocklessThreats": "true",
    "StocklessAggression": "145",
    "StocklessOverdrive": "false",
    "StocklessMobile": "false",
}


def bench(binary: Path, profile: dict[str, str], depth: int, timeout: int) -> BenchResult:
    options = {**DEFAULT_OPTIONS, **profile}
    commands = [f"setoption name {name} value {value}" for name, value in options.items()]
    commands += ["isready", f"bench 16 1 {depth} default depth", "quit", ""]
    proc = subprocess.run(
        [str(binary)],
        cwd=binary.parent,
        input="\n".join(commands),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        encoding="utf-8",
        errors="replace",
        text=True,
        timeout=timeout,
        check=True,
    )
    try:
        return parse_bench(proc.stdout, expected_positions=default_bench_position_count(), depth=depth)
    except ValueError as exc:
        raise ValueError(f"{binary}: invalid bench: {exc}\n{proc.stdout[-2000:]}") from exc


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("baseline", type=Path)
    p.add_argument("candidate", type=Path)
    p.add_argument("--depth", type=int, default=9)
    p.add_argument("--timeout", type=int, default=180)
    args = p.parse_args()
    if args.depth < 1 or args.timeout < 1:
        p.error("depth and timeout must be positive")
    baseline, candidate = [
        binary.resolve(strict=True) for binary in (args.baseline, args.candidate)
    ]
    problems = []
    for name, options in PROFILES.items():
        a = bench(baseline, options, args.depth, args.timeout)
        b = bench(candidate, options, args.depth, args.timeout)
        equivalent = a.positions == b.positions
        print(
            f"{name}: baseline={a.nodes:,} candidate={b.nodes:,}"
            f" positions={len(a.positions)}/{len(b.positions)}"
            f" {'PASS' if equivalent else 'FAIL'}",
            flush=True,
        )
        if not equivalent:
            problems.append(name)
    if problems:
        print(f"FAIL: search decisions differ in {', '.join(problems)}")
        return 1
    print(f"PASS: {len(PROFILES)} UCI profiles preserve per-position nodes, scores, PVs and bestmoves")
    print("This is a semantics check. NPS and Elo must be evaluated separately.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
