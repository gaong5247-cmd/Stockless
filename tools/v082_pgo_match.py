#!/usr/bin/env python3
"""One clean A/B: modern Stockless PGO vs identical source without PGO.

This is only a measurement, not a new search heuristic or NNUE training.
"""
from __future__ import annotations

import argparse
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path

from history_stats import analyze_pgn, format_result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cutechess", type=Path, required=True)
    parser.add_argument("--pgo", type=Path, required=True)
    parser.add_argument("--standard", type=Path, required=True)
    parser.add_argument("--book", type=Path, required=True)
    parser.add_argument("--games", type=int, default=200)
    parser.add_argument("--tc", default="0.2+0.002")
    parser.add_argument("--concurrency", type=int, default=2)
    parser.add_argument("--out", type=Path, default=Path("results/pgo-ab"))
    args = parser.parse_args()

    if args.games < 2 or args.games % 2:
        parser.error("Games must be a positive even number")
    if args.concurrency not in range(1, 5):
        parser.error("Concurrency must be 1..4")
    binaries = [args.cutechess, args.pgo, args.standard, args.book]
    for item in binaries:
        if not item.is_file():
            parser.error(f"Missing file: {item}")
    if args.pgo.resolve() == args.standard.resolve():
        parser.error("PGO and standard must be distinct executable paths")

    args.out.mkdir(parents=True, exist_ok=True)
    pgn = args.out / "pgo-vs-standard.pgn"
    log = args.out / "pgo-vs-standard.log"

    def engine(name: str, exe: Path) -> list[str]:
        return [
            "-engine", f"name={name}", f"cmd={exe.resolve()}",
            f"dir={exe.resolve().parent}",
            "option.Threads=1", "option.Hash=32", "option.MoveOverhead=1",
            "option.StocklessHybrid=true", "option.StocklessAggression=145",
            "option.StocklessThreats=true", "option.StocklessOverdrive=false",
            "option.StocklessMobile=false", "option.StocklessThreatHistory=false",
            "option.StocklessSearchProfile=0",
        ]

    cmd = [
        str(args.cutechess.resolve()), "-tournament", "round-robin",
        *engine("ModernPGO", args.pgo),
        *engine("ModernStandard", args.standard),
        "-each", "proto=uci", f"tc={args.tc}",
        "-games", str(args.games), "-repeat",
        "-concurrency", str(args.concurrency),
        "-openings", f"file={args.book.resolve()}",
        "format=epd", "order=random", "-srand", "20261020",
        "-draw", "movenumber=40", "movecount=8", "score=10",
        "-pgnout", str(pgn.resolve()),
    ]
    with log.open("w", encoding="utf-8") as stream:
        completed = subprocess.run(cmd, stdout=stream,
                                   stderr=subprocess.STDOUT, check=False)
    if completed.returncode:
        raise RuntimeError(f"Cute Chess error {completed.returncode}. See {log}")

    stats = analyze_pgn(pgn, "ModernPGO", "ModernStandard", expected_games=args.games)
    (args.out / "summary.json").write_text(
        json.dumps(
            {
                "date_utc": datetime.now(timezone.utc).isoformat(),
                "comparison": "Same modern source + same ISA; PGO vs non-PGO",
                "book": str(args.book.resolve()),
                "time_control": args.tc,
                "result": stats,
                "confidence_note": "Approximate game-level CI; paired openings correlated",
                "no_auto_promotion": True,
            },
            ensure_ascii=False, indent=2
        ) + "\n", encoding="utf-8",
    )
    print(format_result("Modern PGO vs identical non-PGO", stats), flush=True)


if __name__ == "__main__":
    main()
