#!/usr/bin/env python3
"""PGN statistics for reproducible Stockless self-play and Stockfish matches.

Confidence intervals are approximate fixed-sample game-level intervals. Opening
correlation and other run-to-run effects are not represented; no automatic
promotion may rely on a screening match alone.
"""
from __future__ import annotations

import math
from pathlib import Path
from statistics import variance

import chess.pgn

Z95 = 1.959963984540054
ELO_SCALE = 400.0 / math.log(10.0)


def _elo(score: float) -> float:
    if score <= 0.0:
        return -math.inf
    if score >= 1.0:
        return math.inf
    return 400.0 * math.log10(score / (1.0 - score))


def _result_for(headers: dict[str, str], target: str, opponent: str) -> float:
    white = headers.get("White")
    black = headers.get("Black")
    if {white, black} != {target, opponent}:
        raise ValueError(
            f"PGN contains unexpected opponents: {white!r} vs {black!r}; "
            f"expected {target!r} and {opponent!r}"
        )
    result = headers.get("Result")
    if result not in {"1-0", "0-1", "1/2-1/2"}:
        raise ValueError(f"Unfinished or malformed game result: {result!r}")
    termination = headers.get("Termination", "").lower()
    if any(word in termination for word in ("illegal", "crash", "disconnect", "stall", "abandon")):
        raise ValueError(f"Engine malfunction in PGN: {headers.get('Termination')}")
    if result == "1/2-1/2":
        return 0.5
    return 1.0 if (result == "1-0") == (white == target) else 0.0


def score_stats(scores: list[float]) -> dict:
    if not scores:
        raise ValueError("No finished games to analyze")
    if any(s not in (0.0, 0.5, 1.0) for s in scores):
        raise ValueError("Scores must be 0, 0.5 or 1")
    n = len(scores)
    score = sum(scores) / n
    # A 95% CI for the expected score, used *only* for fixed, predeclared
    # confirmation tests. It is approximate and does not model opening clusters.
    sample_var = variance(scores) if n > 1 else 0.25
    se = math.sqrt(max(sample_var, 0.0) / n)
    low = max(0.0, score - Z95 * se)
    high = min(1.0, score + Z95 * se)
    return {
        "games": n,
        "wins": scores.count(1.0),
        "draws": scores.count(0.5),
        "losses": scores.count(0.0),
        "score": round(score, 8),
        "score_se": round(se, 8),
        "score_ci95": [round(low, 8), round(high, 8)],
        "elo": round(_elo(score), 3) if 0 < score < 1 else ("+inf" if score == 1 else "-inf"),
        "elo_ci95": [
            round(_elo(low), 3) if 0 < low < 1 else ("+inf" if low == 1 else "-inf"),
            round(_elo(high), 3) if 0 < high < 1 else ("+inf" if high == 1 else "-inf"),
        ],
        "method": "fixed-sample game-level 95% normal CI (approximate; opening correlation excluded)",
    }


def analyze_pgn(
    path: str | Path,
    target: str,
    opponent: str,
    expected_games: int | None = None,
) -> dict:
    path = Path(path)
    scores: list[float] = []
    with path.open("r", encoding="utf-8", errors="replace") as handle:
        while game := chess.pgn.read_game(handle):
            if game.errors:
                raise ValueError(f"Malformed PGN in {path}: {game.errors[0]}")
            scores.append(_result_for(game.headers, target, opponent))

    if expected_games is not None and len(scores) != expected_games:
        raise ValueError(
            f"{path}: expected {expected_games} completed games, found {len(scores)}"
        )
    result = score_stats(scores)
    result.update({"pgn": str(path), "target": target, "opponent": opponent})
    return result


def compare_stockfish(candidate: dict, baseline: dict) -> dict:
    """Two independent matches vs *the same* Stockfish build and time control."""
    p = float(candidate["score"]) - float(baseline["score"])
    se = math.sqrt(
        float(candidate["score_se"]) ** 2 + float(baseline["score_se"]) ** 2
    )
    lo, hi = p - Z95 * se, p + Z95 * se
    return {
        "score_difference": round(p, 8),
        "se": round(se, 8),
        "ci95": [round(lo, 8), round(hi, 8)],
        "units": "fraction of points per game; positive means candidate better",
    }


def elo_text(value: float | str) -> str:
    return f"{value:+.2f}" if isinstance(value, (float, int)) else str(value)


def format_result(label: str, stat: dict) -> str:
    return (
        f"{label}: {stat['games']} games W/D/L="
        f"{stat['wins']}/{stat['draws']}/{stat['losses']} "
        f"score={100 * stat['score']:.2f}% Elo={elo_text(stat['elo'])} "
        f"CI95=[{elo_text(stat['elo_ci95'][0])}, "
        f"{elo_text(stat['elo_ci95'][1])}]"
    )
