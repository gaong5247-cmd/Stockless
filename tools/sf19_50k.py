#!/usr/bin/env python3
"""Fixed 50,000-game Stockless v0.9.0 versus Stockfish 19 paired-color protocol."""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import math
import random
import statistics
import zipfile
from collections import Counter
from pathlib import Path

import chess.pgn

SEED = 20261026
PAIRS = 25_000
SHARDS = 200
PAIRS_PER_SHARD = PAIRS // SHARDS
GAMES_PER_SHARD = PAIRS_PER_SHARD * 2
SOURCE_BOOK = "official-stockfish/books@a804a97e709f40aa75a00f9d19e84915b7a3a45c/8moves_v3.pgn.zip"
CANDIDATE_SHA = "1f1a4870fb02cc6cd04d52e2e082ef72aed0ff46"
OPPONENT_SHA = "edb0d9db6731067ec50ce619ff372b463bc4dd5d"
TIME_CONTROL = "10+0.1"
PLAYERS = ("Stockfish19", "Stockless")


def checksum(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save(path: Path, obj: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def prepare(archive: Path, output: Path) -> None:
    with zipfile.ZipFile(archive) as z:
        files = [p for p in z.namelist() if p.lower().endswith(".pgn")]
        if len(files) != 1:
            raise ValueError(f"Expected exactly one PGN in book ZIP: {files}")
        stream = io.StringIO(z.read(files[0]).decode("utf-8-sig"))
    positions = set()
    read_games = 0
    while (game := chess.pgn.read_game(stream)) is not None:
        if game.errors:
            raise ValueError(f"Invalid official book PGN at game {read_games}: {game.errors}")
        start = game.end().board()
        if not start.is_game_over():
            positions.add(start.epd(en_passant="legal"))
        read_games += 1
    ordered = sorted(positions)
    random.Random(SEED).shuffle(ordered)
    if len(ordered) < PAIRS:
        raise ValueError(f"Not enough unique opening positions: {len(ordered)} < {PAIRS}")
    selected = ordered[:PAIRS]
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text("\n".join(selected) + "\n", encoding="utf-8")
    save(output.parent / "provenance.json", {
        "protocol": "sf19-50k-v1", "stockless_source_sha": CANDIDATE_SHA,
        "stockfish19_source_sha": OPPONENT_SHA, "book": SOURCE_BOOK,
        "book_zip_sha256": checksum(archive), "random_seed": SEED,
        "read_book_games": read_games, "unique_book_positions": len(positions),
        "selected_openings_sha256": checksum(output), "selected_openings": PAIRS,
        "games": 2 * PAIRS, "time_control": TIME_CONTROL, "shards": SHARDS,
        "games_per_shard": GAMES_PER_SHARD,
    })


def split(book: Path, shard: int, output: Path) -> None:
    if not 0 <= shard < SHARDS:
        raise ValueError(f"Shard must be in [0,{SHARDS})")
    lines = book.read_text(encoding="utf-8").splitlines()
    if len(lines) != PAIRS or len(set(lines)) != PAIRS:
        raise ValueError("Master book must contain exactly 25,000 unique EPDs")
    selected = lines[shard * PAIRS_PER_SHARD:(shard + 1) * PAIRS_PER_SHARD]
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text("\n".join(selected) + "\n", encoding="utf-8")


def points(result: str, candidate_is_white: bool) -> float:
    if result == "1/2-1/2":
        return 0.5
    if result not in ("1-0", "0-1"):
        raise ValueError(f"Unfinished/invalid result: {result}")
    won_by_white = result == "1-0"
    return 1.0 if won_by_white == candidate_is_white else 0.0


def validate(shard: int, pgn: Path, starts_file: Path, summary_file: Path,
             candidate_digest: str, opponent_digest: str) -> None:
    expected = set(starts_file.read_text(encoding="utf-8").splitlines())
    if len(expected) != PAIRS_PER_SHARD:
        raise ValueError("Wrong number of distinct shard opening positions")
    pairs: dict[str, dict[str, float]] = {}
    termination: Counter[str] = Counter()
    wdl: Counter[str] = Counter()
    with pgn.open(encoding="utf-8-sig", errors="replace") as stream:
        n = 0
        while (game := chess.pgn.read_game(stream)) is not None:
            n += 1
            if game.errors:
                raise ValueError(f"Game {n} contains PGN errors: {game.errors}")
            white, black = game.headers.get("White"), game.headers.get("Black")
            if sorted((white, black)) != list(PLAYERS):
                raise ValueError(f"Game {n} engine identities wrong: {white}, {black}")
            result = game.headers.get("Result", "*")
            if result not in ("1-0", "0-1", "1/2-1/2"):
                raise ValueError(f"Game {n} missing completed result: {result}")
            key = game.board().epd(en_passant="legal")
            if key not in expected:
                raise ValueError(f"Game {n} has unexpected start: {key}")
            side = "white" if white == "Stockless" else "black"
            section = pairs.setdefault(key, {})
            if side in section:
                raise ValueError(f"Duplicate {side} game for opening {key}")
            score = points(result, side == "white")
            section[side] = score
            wdl["W" if score == 1 else "L" if score == 0 else "D"] += 1
            termination[game.headers.get("Termination", "unspecified")] += 1
    if n != GAMES_PER_SHARD or len(pairs) != PAIRS_PER_SHARD:
        raise ValueError(f"Shard incomplete: games={n}, pairs={len(pairs)}")
    if set(pairs) != expected or any(set(s) != {"white", "black"} for s in pairs.values()):
        raise ValueError("Color-swapped pairing / unique-opening validation failed")
    save(summary_file, {
        "schema": 1, "protocol": "sf19-50k-v1", "shard": shard,
        "stockless_source_sha": CANDIDATE_SHA, "stockfish19_source_sha": OPPONENT_SHA,
        "candidate_binary_sha256": candidate_digest,
        "opponent_binary_sha256": opponent_digest,
        "time_control": TIME_CONTROL, "games": n, "pairs": len(pairs),
        "wdl": dict(wdl), "terminations": dict(termination),
        "selected_openings_sha256": checksum(starts_file),
        "pgn_sha256": checksum(pgn), "score_by_opening": pairs,
    })


def elo(score: float) -> float:
    if score <= 0 or score >= 1:
        return float("-inf") if score <= 0 else float("inf")
    return -400 * math.log10(1 / score - 1)


def aggregate(folder: Path, result: Path, report: Path) -> None:
    filenames = list(folder.glob("summary-*.json"))
    if len(filenames) != SHARDS:
        raise ValueError(f"Expected {SHARDS} shard summaries, got {len(filenames)}")
    shards = {}
    all_pairs = {}
    wdl: Counter[str] = Counter()
    expected_cand = expected_opp = None
    for p in filenames:
        s = json.loads(p.read_text(encoding="utf-8"))
        i = s["shard"]
        if i in shards or i not in range(SHARDS):
            raise ValueError(f"Repeated/invalid shard ID: {i}")
        shards[i] = s
        if s["protocol"] != "sf19-50k-v1" or s["time_control"] != TIME_CONTROL:
            raise ValueError(f"Protocol/settings differ in shard {i}")
        if s["stockless_source_sha"] != CANDIDATE_SHA or s["stockfish19_source_sha"] != OPPONENT_SHA:
            raise ValueError(f"Engine source differs in shard {i}")
        if (s["games"], s["pairs"]) != (GAMES_PER_SHARD, PAIRS_PER_SHARD):
            raise ValueError(f"Incomplete shard {i}")
        if expected_cand is None:
            expected_cand, expected_opp = s["candidate_binary_sha256"], s["opponent_binary_sha256"]
        if (expected_cand, expected_opp) != (s["candidate_binary_sha256"], s["opponent_binary_sha256"]):
            raise ValueError("Mismatched binaries across shards")
        for k, v in s["score_by_opening"].items():
            if k in all_pairs or set(v) != {"white", "black"}:
                raise ValueError(f"Reused or unpaired opening: {k}")
            all_pairs[k] = (v["white"] + v["black"]) / 2
        wdl.update(s["wdl"])
    if set(shards) != set(range(SHARDS)) or len(all_pairs) != PAIRS:
        raise ValueError("Missing shard or opening")
    if sum(wdl.values()) != PAIRS * 2:
        raise ValueError("Incomplete total WDL")
    vals = list(all_pairs.values())
    score = statistics.mean(vals)
    score_se = statistics.stdev(vals) / math.sqrt(len(vals))
    critical = statistics.NormalDist().inv_cdf(0.975)
    low, high = max(1e-9, score - critical * score_se), min(1 - 1e-9, score + critical * score_se)
    pentanomial = Counter(vals)
    outcome = {
        "protocol": "sf19-50k-v1", "completed": True,
        "games": PAIRS * 2, "color_swapped_pairs": PAIRS, "shards": SHARDS,
        "time_control": TIME_CONTROL, "stockless_source_sha": CANDIDATE_SHA,
        "stockfish19_source_sha": OPPONENT_SHA,
        "stockless_binary_sha256": expected_cand, "stockfish19_binary_sha256": expected_opp,
        "wdl": dict(wdl), "pentanomial_0_025_05_075_1": [pentanomial.get(x, 0) for x in (0, .25, .5, .75, 1)],
        "stockless_score": score, "score_standard_error": score_se,
        "score_pair_cluster_ci95": [low, high],
        "elo_difference_stockless_minus_sf19": elo(score),
        "elo_pair_cluster_ci95": [elo(low), elo(high)],
        "method": "Fixed 25,000 independent starting-position pairs, approximate normal 95% CI on pair means",
        "note": "Ratings are relative to tested Stockfish 19, build/hardware and time control; not an absolute Elo rating",
    }
    save(result, outcome)
    lines = ["# Stockless v0.9.0 vs official Stockfish 19 — 50,000 games", "",
             f"**Games:** {PAIRS*2:,} / **color-swapped opening pairs:** {PAIRS:,}",
             f"**Time control:** {TIME_CONTROL} seconds, 1 thread, 64 MiB hash per engine.",
             f"**Stockless W/D/L:** {wdl['W']:,} / {wdl['D']:,} / {wdl['L']:,}",
             f"**Stockless score:** {100*score:.4f}%",
             f"**Estimated relative Elo:** {elo(score):+.3f}",
             f"**Approximate paired 95% CI (Elo):** {elo(low):+.3f} to {elo(high):+.3f}",
             "", "Opening pairs and shard results were checked for completeness, color reversal, binary identity and no overlap.",
             "This does not directly establish an absolute 3635-Elo scale or platform-independent strength."]
    report.parent.mkdir(parents=True, exist_ok=True)
    report.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(report.read_text(encoding="utf-8"))


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest="cmd", required=True)
    b = sub.add_parser("prepare")
    b.add_argument("--archive", type=Path, required=True)
    b.add_argument("--output", type=Path, required=True)
    x = sub.add_parser("split")
    x.add_argument("--book", type=Path, required=True)
    x.add_argument("--shard", type=int, required=True)
    x.add_argument("--output", type=Path, required=True)
    v = sub.add_parser("validate")
    v.add_argument("--shard", type=int, required=True)
    v.add_argument("--pgn", type=Path, required=True)
    v.add_argument("--starts", type=Path, required=True)
    v.add_argument("--out", type=Path, required=True)
    v.add_argument("--candidate-sha256", required=True)
    v.add_argument("--opponent-sha256", required=True)
    a = sub.add_parser("aggregate")
    a.add_argument("--folder", type=Path, required=True)
    a.add_argument("--json", type=Path, required=True)
    a.add_argument("--markdown", type=Path, required=True)
    args = p.parse_args()
    if args.cmd == "prepare":
        prepare(args.archive, args.output)
    elif args.cmd == "split":
        split(args.book, args.shard, args.output)
    elif args.cmd == "validate":
        validate(args.shard, args.pgn, args.starts, args.out, args.candidate_sha256, args.opponent_sha256)
    else:
        aggregate(args.folder, args.json, args.markdown)


if __name__ == "__main__":
    main()
