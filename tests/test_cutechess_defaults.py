#!/usr/bin/env python3
"""Regression test: arena command options must match the real Stockless UCI defaults."""
from __future__ import annotations

import os
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RUNNER = ROOT / "scripts" / "run-cutechess-match.sh"


def inspect_args(overrides: dict[str, str], opponent_name: str = "Stockfish") -> list[str]:
    with tempfile.TemporaryDirectory() as directory:
        tmp = Path(directory)
        fake_cute = tmp / "cutechess-cli"
        fake_cute.write_text('#!/bin/sh\nprintf "%s\n" "$@" > "$DUMP_ARGS"\n', encoding="utf-8")
        fake_cute.chmod(0o755)

        env = os.environ.copy()
        for key in ("STOCKLESS_AGGRESSION", "STOCKLESS_OVERDRIVE", "STOCKLESS_THREATS",
                    "STOCKLESS_MOBILE", "STOCKLESS_OPENING_FORMAT", "OPPONENT_MOVE_OVERHEAD_OPTION"):
            env.pop(key, None)
        env.update(overrides)
        env.update(
            CUTECHESS=str(fake_cute),
            DUMP_ARGS=str(tmp / "args.txt"),
            STOCKLESS=str(tmp / "candidate"),
            OPENINGS=str(ROOT / "tests" / "opening_lines.txt"),
        )
        subprocess.run(
            ["bash", str(RUNNER), str(tmp / "opponent"), opponent_name,
             str(tmp / "game.pgn"), "2", "0.1+0.001", "1"],
            check=True,
            env=env,
            cwd=ROOT,
        )
        return (tmp / "args.txt").read_text(encoding="utf-8").splitlines()


def engine_args(args: list[str]) -> tuple[list[str], list[str]]:
    starts = [index for index, value in enumerate(args) if value == "-engine"]
    assert len(starts) == 2, f"Expected exactly two engines: {args}"
    return args[starts[0] + 1:starts[1]], args[starts[1] + 1:args.index("-each")]


def main() -> None:
    defaults = inspect_args({})
    for expected in ("option.StocklessHybrid=true", "option.StocklessAggression=145",
                     "option.StocklessOverdrive=false", "option.StocklessThreats=true",
                     "option.StocklessMobile=false"):
        assert expected in defaults, f"Wrong default {expected}: {defaults}"

    # Names containing spaces must reach CuteChess as one argv item. Stockless
    # and Stockfish advertise "Move Overhead"; pinned Reckless uses "MoveOverhead".
    for engine in engine_args(defaults):
        assert engine.count("option.Move Overhead=1") == 1, f"Wrong overhead argument: {engine}"
        assert "option.MoveOverhead=1" not in engine, f"Unknown Stockfish option: {engine}"
    candidate, opponent = engine_args(inspect_args({}, opponent_name="Reckless"))
    assert candidate.count("option.Move Overhead=1") == 1
    assert "option.MoveOverhead=1" not in candidate
    assert opponent.count("option.MoveOverhead=1") == 1
    assert "option.Move Overhead=1" not in opponent

    candidate, opponent = engine_args(inspect_args(
        {"OPPONENT_MOVE_OVERHEAD_OPTION": "MoveOverhead"}, opponent_name="CustomEngineLabel"))
    assert candidate.count("option.Move Overhead=1") == 1
    assert opponent.count("option.MoveOverhead=1") == 1
    assert "option.Move Overhead=1" not in opponent

    custom = inspect_args({"STOCKLESS_AGGRESSION": "165",
                           "STOCKLESS_OVERDRIVE": "true",
                           "STOCKLESS_THREATS": "false",
                           "STOCKLESS_OPENING_FORMAT": "pgn"})
    assert "format=epd" in defaults
    assert "format=pgn" in custom
    for expected in ("option.StocklessAggression=165", "option.StocklessOverdrive=true",
                     "option.StocklessThreats=false"):
        assert expected in custom, f"Overriding {expected} failed: {custom}"
    print("CuteChess defaults, explicit overrides, and engine-specific overhead arguments passed")


if __name__ == "__main__":
    main()
