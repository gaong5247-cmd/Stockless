#!/usr/bin/env python3
"""Generate original teacher-labelled chess CSV via Stockfish self-play.

No fictional game outcomes: '*' and empty actual_result_stm mean unfinished.
UCI_ShowWDL values are MODEL ESTIMATES, not observed outcomes.
"""
from __future__ import annotations

import argparse
import csv
import math
import random
import uuid
from pathlib import Path

import chess
import chess.engine

FIELDS = [
    "game_id", "ply", "fen", "score_cp", "mate", "wdl_win", "wdl_draw", "wdl_loss",
    "depth", "nodes", "best_move", "pv", "attack_pressure", "king_danger",
    "game_result", "actual_result_stm", "teacher",
]


def pressure(board, attacker):
    enemy = not attacker
    king = board.king(enemy)
    if king is None:
        return 0.0
    zone = chess.SquareSet(chess.BB_KING_ATTACKS[king] | chess.BB_SQUARES[king])
    contacts = sum(bool(board.attackers(attacker, sq)) for sq in zone)
    # Distinct contacts and attacking pieces; no outside NNUE model is used.
    attackers = set()
    for sq in zone:
        attackers.update(board.attackers(attacker, sq))
    return min(1.0, (contacts * 0.08 + max(0, len(attackers) - 1) * 0.08))


def wdl_for(info, turn):
    wdl = info.get("wdl")
    if wdl is None:
        raise RuntimeError("Stockfish did not provide UCI_ShowWDL; cannot generate complete CSV")
    p = wdl.pov(turn)
    result = [int(p.wins), int(p.draws), int(p.losses)]
    if sum(result) != 1000:
        raise RuntimeError("UCI WDL must sum to 1000")
    return result


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--engine", required=True, help="Stockfish teacher executable")
    ap.add_argument("--net", default="", help="Optional teacher EvalFile, if not embedded")
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--target-positions", type=int, default=10_000_000)
    ap.add_argument("--depth", type=int, default=12)
    ap.add_argument("--threads", type=int, default=2)
    ap.add_argument("--max-plies", type=int, default=180)
    ap.add_argument("--seed", type=int, default=5247)
    args = ap.parse_args()
    if args.depth < 1 or args.target_positions < 1 or args.max_plies < 4:
        ap.error("Invalid depth/target/max-plies")
    rng = random.Random(args.seed)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    already = 0
    if args.out.exists():
        with args.out.open(newline="", encoding="utf-8") as f:
            already = max(0, sum(1 for _ in f) - 1)
        print(f"Appending to {args.out}: {already} existing positions")
    engine = chess.engine.SimpleEngine.popen_uci(args.engine, timeout=120)
    try:
        cfg = {"Threads": args.threads, "UCI_ShowWDL": True}
        if args.net:
            cfg["EvalFile"] = args.net
        engine.configure(cfg)
        with args.out.open("a", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=FIELDS)
            if already == 0:
                writer.writeheader()
            while already < args.target_positions:
                board = chess.Board()
                game_id = str(uuid.uuid4())
                collected = []
                for ply in range(args.max_plies):
                    if board.is_game_over(claim_draw=True):
                        break
                    info_list = engine.analyse(
                        board, chess.engine.Limit(depth=args.depth), multipv=3
                    )
                    info_list = [x for x in info_list if x.get("pv")]
                    if not info_list:
                        break
                    entries = []
                    for item in info_list:
                        score = item["score"].pov(board.turn)
                        cp = score.score()
                        mate = score.mate()
                        if cp is None and mate is None:
                            continue
                        w, d, l = wdl_for(item, board.turn)
                        entries.append((item, cp, mate, w, d, l))
                    if not entries:
                        break
                    best_cp = entries[0][1]
                    choices = []
                    for idx, item in enumerate(entries):
                        cp = item[1]
                        delta = (best_cp - cp) if best_cp is not None and cp is not None else idx * 80
                        choices.append(math.exp(-max(0, delta) / 35.0) if delta <= 100 else 0.0)
                    chosen = rng.choices(entries, weights=choices, k=1)[0]
                    info, cp, mate, w, d, l = chosen
                    move = info["pv"][0]
                    if move not in board.legal_moves:
                        raise RuntimeError("Teacher emitted illegal move")
                    collected.append({
                        "game_id": game_id, "ply": ply, "fen": board.fen(),
                        "score_cp": cp if cp is not None else "", "mate": mate if mate is not None else "",
                        "wdl_win": w, "wdl_draw": d, "wdl_loss": l,
                        "depth": info.get("depth", args.depth), "nodes": info.get("nodes", 0),
                        "best_move": info_list[0]["pv"][0].uci(),
                        "pv": " ".join(m.uci() for m in info.get("pv", [])[:16]),
                        "attack_pressure": round(pressure(board, board.turn), 5),
                        "king_danger": round(pressure(board, not board.turn), 5),
                        "_turn": board.turn,
                    })
                    board.push(move)
                outcome = board.outcome(claim_draw=True)
                result = board.result(claim_draw=True) if outcome else "*"
                for row in collected[:max(0, args.target_positions - already)]:
                    row["game_result"] = result
                    row["actual_result_stm"] = (
                        "" if outcome is None else
                        (0.5 if outcome.winner is None else int(outcome.winner == row["_turn"]))
                    )
                    row.pop("_turn")
                    row["teacher"] = args.engine
                    writer.writerow(row)
                    already += 1
                f.flush()
                print(f"positions={already:,}/{args.target_positions:,} game={game_id[:8]} result={result}", flush=True)
    finally:
        engine.quit()


if __name__ == "__main__":
    main()
