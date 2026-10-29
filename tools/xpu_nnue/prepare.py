#!/usr/bin/env python3
"""Stream teacher CSV into compact native-feature records (no giant RAM arrays).

Data format is internal to our independently written XPU trainer; it is not
a replacement for Stockfish's .nnue serialization or official binpack.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import math
import sqlite3
import struct
import subprocess
from pathlib import Path

import chess

RECORD = struct.Struct("<B128siiiifff")


def win_rate_a(board: chess.Board) -> float:
    # Same material-dependent CP scaling as pinned Stockfish's uci.cpp.
    material = (
        len(board.pieces(chess.PAWN, chess.WHITE)) + len(board.pieces(chess.PAWN, chess.BLACK))
        + 3 * sum(len(board.pieces(chess.KNIGHT, side)) + len(board.pieces(chess.BISHOP, side))
                  for side in chess.COLORS)
        + 5 * sum(len(board.pieces(chess.ROOK, side)) for side in chess.COLORS)
        + 9 * sum(len(board.pieces(chess.QUEEN, side)) for side in chess.COLORS)
    )
    m = max(17, min(78, material)) / 58.0
    return ((-142.72052667 * m + 372.35176398) * m - 340.71073572) * m + 415.23490212


class StockfishProbe:
    def __init__(self, executable: str, net: str):
        self.proc = subprocess.Popen(
            [executable], stdin=subprocess.PIPE, stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL, encoding="utf-8", bufsize=1
        )
        self.say("uci")
        self.wait_for("uciok")
        self.say(f"setoption name EvalFile value {Path(net).resolve()}")
        self.say("isready")
        self.wait_for("readyok")

    def say(self, line: str):
        self.proc.stdin.write(line + "\n")
        self.proc.stdin.flush()

    def wait_for(self, marker: str):
        for _ in range(300):
            line = self.proc.stdout.readline()
            if not line:
                raise RuntimeError(f"Stockfish probe exited unexpectedly before {marker}")
            if line.strip() == marker:
                return
        raise RuntimeError(f"Probe never emitted {marker}")

    def feature(self, fen: str):
        self.say(f"position fen {fen}")
        self.say("stockless_features")
        while True:
            line = self.proc.stdout.readline()
            if not line:
                raise RuntimeError("Probe exited / command not installed; run patch_probe.py and rebuild")
            if line.startswith("stockless_features "):
                parts = line.split()
                if len(parts) != 6:
                    raise RuntimeError("Corrupt native probe output")
                bucket, psqt, skip, raw = map(int, parts[1:5])
                a = [int(x) for x in parts[5].split(",")]
                if not 0 <= bucket < 8 or len(a) != 128 or any(not 0 <= v <= 255 for v in a):
                    raise RuntimeError("Unexpected NNUE feature payload")
                return bucket, bytes(a), psqt, skip, raw

    def close(self):
        if self.proc.poll() is None:
            try:
                self.say("quit")
                self.proc.wait(timeout=5)
            except (OSError, subprocess.TimeoutExpired):
                self.proc.kill()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv", type=Path, required=True)
    ap.add_argument("--probe", required=True, help="Built Stockless with stockless_features UCI command")
    ap.add_argument("--net", required=True, help="The EXACT base net loaded in probe")
    ap.add_argument("--out", type=Path, required=True, help="Directory for train.bin/val.bin/test.bin")
    ap.add_argument("--max-records", type=int, default=0)
    args = ap.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    dbpath = args.out / "dedup.sqlite3"
    db = sqlite3.connect(dbpath)
    db.execute("PRAGMA journal_mode=WAL")
    db.execute("CREATE TABLE IF NOT EXISTS seen (hash BLOB PRIMARY KEY)")
    counts = {"train": 0, "val": 0, "test": 0, "skipped": 0}
    probe = StockfishProbe(args.probe, args.net)
    handles = {k: (args.out / (k + ".bin")).open("wb") for k in ("train", "val", "test")}
    try:
        with args.csv.open("r", newline="", encoding="utf-8") as csvfile:
            reader = csv.DictReader(csvfile)
            required = {"fen", "game_id", "score_cp", "wdl_win", "wdl_draw",
                        "wdl_loss", "attack_pressure", "king_danger"}
            if not required.issubset(reader.fieldnames or []):
                raise ValueError(f"Missing columns: {required - set(reader.fieldnames or [])}")
            for index, row in enumerate(reader):
                if args.max_records and index >= args.max_records:
                    break
                if not row["score_cp"] or row.get("mate"):
                    counts["skipped"] += 1
                    continue
                cp = float(row["score_cp"])
                if not math.isfinite(cp) or abs(cp) > 1200:
                    counts["skipped"] += 1
                    continue
                wdl = [int(row[key]) for key in ("wdl_win", "wdl_draw", "wdl_loss")]
                if min(wdl) < 0 or sum(wdl) != 1000:
                    raise ValueError(f"Invalid WDL on CSV row {index + 2}")
                board = chess.Board(row["fen"])
                if not board.is_valid():
                    raise ValueError(f"Illegal FEN on row {index + 2}")
                # De-duplicate across ALL splits: no identical board in train and validation.
                key = " ".join(row["fen"].split()[:4]).encode("utf-8")
                digest = hashlib.blake2b(key, digest_size=16).digest()
                try:
                    db.execute("INSERT INTO seen(hash) VALUES (?)", (digest,))
                except sqlite3.IntegrityError:
                    counts["skipped"] += 1
                    continue
                h = hashlib.blake2b(row["game_id"].encode(), digest_size=2).digest()
                n = int.from_bytes(h, "little") % 100
                split = "test" if n < 5 else ("val" if n < 10 else "train")
                bucket, features, psqt, skip, raw = probe.feature(row["fen"])
                native_target = int(round(cp * win_rate_a(board) / 100.0))
                attack = max(0., min(1., float(row["attack_pressure"]) - 0.65 * float(row["king_danger"])))
                handles[split].write(RECORD.pack(
                    bucket, features, psqt, skip, raw, native_target, attack,
                    wdl[0] / 1000.0, wdl[2] / 1000.0
                ))
                counts[split] += 1
                if index % 10000 == 0:
                    db.commit()
                    print(index + 1, counts, flush=True)
        db.commit()
        print("Finished:", counts)
    finally:
        for f in handles.values():
            f.close()
        probe.close()
        db.close()


if __name__ == "__main__":
    main()
