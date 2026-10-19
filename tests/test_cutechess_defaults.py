#!/usr/bin/env python3
"""Regression test: arena command options must match the real Stockless UCI defaults."""
from __future__ import annotations

import os
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RUNNER = ROOT / "scripts" / "run-cutechess-match.sh"


def inspect_args(overrides: dict[str, str]) -> list[str]:
    with tempfile.TemporaryDirectory() as directory:
        tmp = Path(directory)
        fake_cute = tmp / "cutechess-cli"
        fake_cute.write_text('#!/bin/sh\nprintf "%s\n" "$@" > "$DUMP_ARGS"\n', encoding="utf-8")
        fake_cute.chmod(0o755)

        env = os.environ.copy()
        for key in ("STOCKLESS_AGGRESSION", "STOCKLESS_OVERDRIVE", "STOCKLESS_THREATS",
                    "STOCKLESS_MOBILE", "STOCKLESS_OPENING_FORMAT"):
            env.pop(key, None)
        env.update(overrides)
        env.update(
            CUTECHESS=str(fake_cute),
            DUMP_ARGS=str(tmp / "args.txt"),
            STOCKLESS=str(tmp / "candidate"),
            OPENINGS=str(ROOT / "tests" / "opening_lines.txt"),
        )
        subprocess.run(
            ["bash", str(RUNNER), str(tmp / "opponent"), "Stockfish",
             str(tmp / "game.pgn"), "2", "0.1+0.001", "1"],
            check=True,
            env=env,
            cwd=ROOT,
        )
        return (tmp / "args.txt").read_text(encoding="utf-8").splitlines()


def main() -> None:
    defaults = inspect_args({})
    for expected in ("option.StocklessHybrid=true", "option.StocklessAggression=145",
                     "option.StocklessOverdrive=false", "option.StocklessThreats=true",
                     "option.StocklessMobile=false"):
        assert expected in defaults, f"Wrong default {expected}: {defaults}"

    custom = inspect_args({"STOCKLESS_AGGRESSION": "165",
                           "STOCKLESS_OVERDRIVE": "true",
                           "STOCKLESS_THREATS": "false",
                           "STOCKLESS_OPENING_FORMAT": "pgn"})
    assert "format=epd" in defaults
    assert "format=pgn" in custom
    for expected in ("option.StocklessAggression=165", "option.StocklessOverdrive=true",
                     "option.StocklessThreats=false"):
        assert expected in custom, f"Overriding {expected} failed: {custom}"
    print("CuteChess default and explicit override regression checks passed")


if __name__ == "__main__":
    main()
