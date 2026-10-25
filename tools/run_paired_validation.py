#!/usr/bin/env python3
"""Reproducible, bounded validation against the frozen v0.8.9 release.

The screening positions are disjoint from both confirmation stages. A single
candidate is frozen before confirmation; the sample size never depends on its
running score. Install chess==1.11.2 to parse the official opening book.
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
from pathlib import Path
import random
import subprocess
import sys
import urllib.request
import zipfile

import chess
import chess.pgn

BASELINE_SHA = "d2e165a6ab70a9a00e1d52ba2a0f4f678ffef22f"
BOOK_REV = "a804a97e709f40aa75a00f9d19e84915b7a3a45c"
BOOK_URL = f"https://raw.githubusercontent.com/official-stockfish/books/{BOOK_REV}/8moves_v3.pgn.zip"
SEED = 20261025
# (games per shard, shard count, time control, first opening index)
STAGES = {
    "screen": (512, 1, "1+0.01", 0),
    "short": (512, 8, "2+0.02", 256),
    "long": (256, 4, "5+0.05", 2304),
}


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def prepare_book(output: Path) -> None:
    with urllib.request.urlopen(BOOK_URL, timeout=120) as response:
        archive_bytes = response.read()
    with zipfile.ZipFile(io.BytesIO(archive_bytes)) as archive:
        names = [name for name in archive.namelist() if name.endswith(".pgn")]
        if len(names) != 1:
            raise RuntimeError(f"Expected one official PGN, got {names}")
        stream = io.StringIO(archive.read(names[0]).decode("utf-8-sig"))
    positions = {}
    while (game := chess.pgn.read_game(stream)) is not None:
        if game.errors:
            raise RuntimeError(f"Malformed official opening: {game.errors}")
        board = game.end().board()
        if board.is_game_over():
            continue
        # First four fields identify a position independently of counters.
        epd = board.epd(en_passant="legal")
        positions.setdefault(epd, epd)
    openings = sorted(positions)
    random.Random(SEED).shuffle(openings)
    if len(openings) < 2816:
        raise RuntimeError(f"Insufficient unique positions: {len(openings)}")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text("\n".join(openings) + "\n", encoding="utf-8")
    provenance = {
        "source": BOOK_URL, "revision": BOOK_REV, "seed": SEED,
        "archive_sha256": hashlib.sha256(archive_bytes).hexdigest(),
        "opening_pool_sha256": digest(output), "unique_positions": len(openings),
        "stages": STAGES,
    }
    output.with_suffix(".json").write_text(json.dumps(provenance, indent=2) + "\n")
    print(json.dumps(provenance, indent=2))


def make_plan(candidate_sha: str, mode: str, output: Path) -> None:
    if mode == "exploratory":
        names = ["screen"]
    else:
        names = ["short", "long"]
    stages = []
    for name in names:
        games, count, tc, _ = STAGES[name]
        stages.append({
            "name": name, "time_control": tc, "minimum_games": games * count,
            "min_elo": 5.0 if name == "short" else 0.0,
            "shards": [{"directory": f"{name}-{index}", "games": games}
                       for index in range(count)],
        })
    plan = {
        "schema": 1, "mode": mode,
        "candidate_name": "StocklessCandidate", "baseline_name": "StocklessBaseline",
        "candidate_sha": candidate_sha, "baseline_sha": BASELINE_SHA,
        "stages": stages,
    }
    output.write_text(json.dumps(plan, indent=2) + "\n")


def run_match(args: argparse.Namespace) -> None:
    games, count, tc, offset = STAGES[args.stage]
    if not 0 <= args.shard < count:
        raise ValueError("Invalid shard index")
    candidate = args.candidate.resolve(strict=True)
    baseline = args.baseline.resolve(strict=True)
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    pool = args.book.read_text(encoding="utf-8").splitlines()
    first = offset + args.shard * (games // 2)
    selected = pool[first:first + games // 2]
    if len(selected) != games // 2 or len(set(selected)) != len(selected):
        raise RuntimeError("Missing or duplicate opening positions")
    openings = output / "openings.epd"
    openings.write_text("\n".join(selected) + "\n", encoding="utf-8")
    command = [
        str(args.cutechess.resolve(strict=True)),
        "-engine", "name=StocklessCandidate", f"cmd={candidate}",
        "-engine", "name=StocklessBaseline", f"cmd={baseline}",
        "option.StocklessThreatHistory=false",
        "-each", "proto=uci", f"tc={tc}", "option.Threads=1", "option.Hash=32",
        "option.StocklessHybrid=true", "option.StocklessAggression=145",
        "option.StocklessThreats=true", "option.StocklessOverdrive=false",
        "option.StocklessMobile=false", "option.Move Overhead=10",
        "-tournament", "gauntlet", "-rounds", str(games // 2), "-games", "2",
        "-repeat", "-openings", f"file={openings}", "format=epd", "order=sequential",
        "-srand", str(SEED), "-concurrency", "2", "-wait", "10",
        "-draw", "movenumber=40", "movecount=8", "score=8",
        "-resign", "movecount=3", "score=650", "-ratinginterval", "64",
        "-pgnout", str(output / "match.pgn"),
    ]
    metadata = {
        "schema": 1, "candidate_sha": args.candidate_sha, "baseline_sha": BASELINE_SHA,
        "candidate_name": "StocklessCandidate", "baseline_name": "StocklessBaseline",
        "time_control": tc, "games": games, "opening_sha256": digest(openings),
        "candidate_binary_sha256": digest(candidate),
        "baseline_binary_sha256": digest(baseline), "command": command,
        "returncode": None, "stage": args.stage, "shard": args.shard,
        "runner": os.environ.get("RUNNER_NAME", "local"),
    }
    metadata_path = output / "metadata.json"
    metadata_path.write_text(json.dumps(metadata, indent=2) + "\n")
    print(json.dumps({"stage": args.stage, "shard": args.shard, "games": games,
                      "time_control": tc, "candidate_sha": args.candidate_sha}), flush=True)
    with (output / "match.log").open("w", encoding="utf-8") as log:
        proc = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                text=True, encoding="utf-8", errors="replace")
        assert proc.stdout is not None
        for line in proc.stdout:
            log.write(line)
            log.flush()
            print(line, end="", flush=True)
        metadata["returncode"] = proc.wait()
    metadata_path.write_text(json.dumps(metadata, indent=2) + "\n")
    if metadata["returncode"] != 0:
        raise RuntimeError(f"CuteChess exited {metadata['returncode']}; evidence is invalid")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    book = commands.add_parser("prepare-book")
    book.add_argument("output", type=Path)
    plan = commands.add_parser("plan")
    plan.add_argument("--candidate-sha", required=True)
    plan.add_argument("--mode", choices=["exploratory", "confirmation"], required=True)
    plan.add_argument("--output", type=Path, required=True)
    run = commands.add_parser("run")
    run.add_argument("--stage", choices=STAGES, required=True)
    run.add_argument("--shard", type=int, required=True)
    for name in ["candidate", "baseline", "cutechess", "book", "output"]:
        run.add_argument(f"--{name}", type=Path, required=True)
    run.add_argument("--candidate-sha", required=True)
    args = parser.parse_args()
    if args.command == "prepare-book":
        prepare_book(args.output)
    elif args.command == "plan":
        make_plan(args.candidate_sha, args.mode, args.output)
    else:
        run_match(args)


if __name__ == "__main__":
    main()
