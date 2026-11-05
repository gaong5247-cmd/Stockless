#!/usr/bin/env python3
"""Compare unchanged-depth Stockless builds on the pinned Stockfish bench.

This measures engine throughput, NOT Elo. Use the same hardware, ISA,
position set, NNUE files and Hash/Threads. For playing strength, use
paired FastChess games with independent openings and time controls.
"""
from __future__ import annotations

import argparse
import re
import statistics
import subprocess
from pathlib import Path

COUNTS = re.compile(r"Nodes searched\s*:\s*([0-9]+)")
NPS = re.compile(r"Nodes/second\s*:\s*([0-9]+)")


def bench(binary: Path, depth: int, timeout: int) -> tuple[int, int]:
    proc = subprocess.run(
        [str(binary), "bench", "16", "1", str(depth), "default", "depth"],
        cwd=binary.parent,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=timeout,
        check=True,
    )
    counts = COUNTS.findall(proc.stdout)
    speeds = NPS.findall(proc.stdout)
    if not counts or not speeds:
        raise RuntimeError(f"No Stockfish bench summary from {binary}:\n{proc.stdout[-2000:]}")
    return int(counts[-1]), int(speeds[-1])


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("baseline", type=Path)
    parser.add_argument("candidate", type=Path)
    parser.add_argument("--depth", type=int, default=10)
    parser.add_argument("--rounds", type=int, default=3)
    parser.add_argument("--timeout", type=int, default=360)
    parser.add_argument(
        "--allow-different-nodes", action="store_true",
        help="Allow changes in search decisions (not suitable for a semantics-preserving speed patch)",
    )
    parser.add_argument(
        "--min-nps-ratio", type=float, default=None,
        help="Optional performance gate, e.g. 0.98; avoid noisy single-run CI assertions",
    )
    args = parser.parse_args()
    if args.rounds < 1 or args.depth < 1:
        parser.error("--depth and --rounds must be positive")

    paths = [p.resolve(strict=True) for p in (args.baseline, args.candidate)]
    for p in paths:
        if not p.is_file():
            parser.error(f"Not a file: {p}")

    results: list[list[tuple[int, int]]] = [[], []]
    for repetition in range(args.rounds):
        # Interleave AB / BA to reduce bias from warmup and thermal drift.
        for engine in ([0, 1] if repetition % 2 == 0 else [1, 0]):
            count, speed = bench(paths[engine], args.depth, args.timeout)
            results[engine].append((count, speed))
            label = "baseline" if engine == 0 else "candidate"
            print(f"round={repetition + 1} {label}: nodes={count} nps={speed:,}", flush=True)

    a_nodes = [t[0] for t in results[0]]
    b_nodes = [t[0] for t in results[1]]
    nodes_differ = (
        len(set(a_nodes)) != 1 or len(set(b_nodes)) != 1 or a_nodes[0] != b_nodes[0]
    )
    if nodes_differ and not args.allow_different_nodes:
        print("FAIL: depth-limited searched node counts differ; inspect decisions before claiming a speed-only patch")
        return 1
    if nodes_differ:
        print("NOTE: search-node counts differ: this is NOT a semantics-preserving speed comparison.")
        print("NPS can be misleading across different search trees; test strength using paired games.")

    speed_a = statistics.median(s for _, s in results[0])
    speed_b = statistics.median(s for _, s in results[1])
    ratio = speed_b / speed_a if speed_a > 0 else 0.0
    print(f"baseline median NPS={speed_a:,.0f}")
    print(f"candidate median NPS={speed_b:,.0f}")
    print(f"candidate / baseline NPS={ratio:.4f} ({100 * (ratio - 1):+.2f}%)")
    print("NPS is not Elo. Run opening-paired games before adopting playing-strength changes.")
    if args.min_nps_ratio is not None and ratio < args.min_nps_ratio:
        print(f"FAIL: ratio {ratio:.4f} < required {args.min_nps_ratio:.4f}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
