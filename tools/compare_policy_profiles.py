#!/usr/bin/env python3
"""Ensure refactored policy preserves bench searches under multiple UCI modes.

Compare binaries compiled with the same Stockfish, NNUE, CPU ISA and flags.
The per-profile node-count and bestmove signatures must agree exactly.
This is a correctness gate, NOT an Elo or speed claim.
"""
from __future__ import annotations

import argparse
import re
import subprocess
from pathlib import Path

NODES = re.compile(r"Nodes searched\s*:\s*(\d+)")
BESTMOVE = re.compile(r"\bbestmove\s+(\S+)")

# Keep all Stockless feature modes represented, including the opt-in ones.
# The mobile+Overdrive combination preserves its v0.8.9 behavior here.
PROFILES = {
    "stockless-default": {},
    "hybrid-off": {"StocklessHybrid": "false"},
    "threats-off": {"StocklessThreats": "false"},
    "aggression-zero": {"StocklessAggression": "0"},
    "aggression-max": {"StocklessAggression": "200"},
    "overdrive-desktop": {"StocklessOverdrive": "true"},
    "overdrive-mobile": {"StocklessOverdrive": "true", "StocklessMobile": "true"},
    "mobile-default": {"StocklessMobile": "true"},
    "experimental-history": {
        "StocklessThreatHistory": "true",
        "StocklessHistoryWeight": "100",
    },
}

DEFAULT_OPTIONS = {
    "Threads": "1",
    "Hash": "16",
    "StocklessHybrid": "true",
    "StocklessThreats": "true",
    "StocklessAggression": "145",
    "StocklessOverdrive": "false",
    "StocklessMobile": "false",
    "StocklessThreatHistory": "false",
    "StocklessHistoryWeight": "100",
}


def bench(binary: Path, profile: dict[str, str], depth: int, timeout: int) -> tuple[int, tuple[str, ...]]:
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
    nodes = NODES.findall(proc.stdout)
    if not nodes:
        raise ValueError(f"{binary}: missing bench node count\n{proc.stdout[-2000:]}")
    return int(nodes[-1]), tuple(BESTMOVE.findall(proc.stdout))


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
        a_nodes, a_moves = bench(baseline, options, args.depth, args.timeout)
        b_nodes, b_moves = bench(candidate, options, args.depth, args.timeout)
        equivalent = a_nodes == b_nodes and a_moves == b_moves
        print(
            f"{name}: baseline={a_nodes:,} candidate={b_nodes:,}"
            f" bestmoves={len(a_moves)}/{len(b_moves)}"
            f" {'PASS' if equivalent else 'FAIL'}",
            flush=True,
        )
        if not equivalent:
            problems.append(name)
    if problems:
        print(f"FAIL: search decisions differ in {', '.join(problems)}")
        return 1
    print(f"PASS: {len(PROFILES)} UCI profiles preserve nodes and PV move signatures")
    print("This is a semantics check. NPS and Elo must be evaluated separately.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
