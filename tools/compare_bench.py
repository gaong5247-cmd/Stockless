#!/usr/bin/env python3
"""Compare unchanged-depth Stockless builds on the pinned Stockfish bench.

This measures engine throughput, NOT Elo. Use the same hardware, ISA,
position set, NNUE files and Hash/Threads. For playing strength, use
paired FastChess games with independent openings and time controls.
"""
from __future__ import annotations

import argparse
import statistics
import subprocess
from pathlib import Path

from bench_output import BenchResult, default_bench_position_count, parse_bench


def bench(binary: Path, depth: int, timeout: int) -> BenchResult:
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
    try:
        return parse_bench(proc.stdout, expected_positions=default_bench_position_count(), depth=depth)
    except ValueError as exc:
        raise RuntimeError(f"Invalid Stockfish bench from {binary}: {exc}\n{proc.stdout[-2000:]}") from exc


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
    if args.rounds < 1 or args.depth < 1 or args.timeout < 1:
        parser.error("--depth, --rounds and --timeout must be positive")

    paths = [p.resolve(strict=True) for p in (args.baseline, args.candidate)]
    for p in paths:
        if not p.is_file():
            parser.error(f"Not a file: {p}")

    results: list[list[BenchResult]] = [[], []]
    for repetition in range(args.rounds):
        # Interleave AB / BA to reduce bias from warmup and thermal drift.
        for engine in ([0, 1] if repetition % 2 == 0 else [1, 0]):
            result = bench(paths[engine], args.depth, args.timeout)
            results[engine].append(result)
            label = "baseline" if engine == 0 else "candidate"
            print(f"round={repetition + 1} {label}: positions={len(result.positions)}"
                  f" nodes={result.nodes} nps={result.nps:,}", flush=True)

    signature = results[0][0].positions
    if not args.allow_different_nodes and any(
        result.positions != signature for engine_results in results for result in engine_results
    ):
        print("FAIL: per-position nodes, scores, PVs or bestmoves differ; inspect decisions before claiming a speed-only patch")
        return 1

    speed_a = statistics.median(result.nps for result in results[0])
    speed_b = statistics.median(result.nps for result in results[1])
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
