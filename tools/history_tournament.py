#!/usr/bin/env python3
"""Stockless history: ON/OFF sweep, independent confirmation, Stockfish match.

All candidates are the SAME executable with different UCI options.
Screening selects a candidate but NEVER decides default promotion.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

from history_stats import analyze_pgn, compare_stockfish, format_result


def engine(name: str, path: Path, enabled: bool | None, weight: int) -> list[str]:
    out = [
        "-engine", f"name={name}", f"cmd={path.resolve()}",
        "option.Threads=1", "option.Hash=32", "option.MoveOverhead=1",
    ]
    if enabled is not None:
        out += [
            "option.StocklessHybrid=true", "option.StocklessAggression=145",
            "option.StocklessThreats=true", "option.StocklessOverdrive=false",
            "option.StocklessMobile=false",
            f"option.StocklessThreatHistory={'true' if enabled else 'false'}",
            f"option.StocklessHistoryWeight={weight}",
        ]
    return out


def match(
    cutechess: Path, stockless: Path, stockfish: Path, directory: Path,
    book: Path, name: str, player: str, weight: int, enabled: bool,
    opponent: str, games: int, tc: str, seed: int, concurrency: int,
) -> dict:
    directory.mkdir(parents=True, exist_ok=True)
    pgn, log = directory / (name + ".pgn"), directory / (name + ".log")
    if not all(p.is_file() for p in (cutechess, stockless, stockfish, book)):
        raise FileNotFoundError(f"Missing required engine or book in {name}")
    a = engine(player, stockless, enabled, weight)
    b = engine(opponent, stockfish, None, 100) if opponent == "StockfishPinned" \
        else engine(opponent, stockless, False, 100)
    cmd = [
        str(cutechess.resolve()), "-tournament", "round-robin", *a, *b,
        "-each", "proto=uci", f"tc={tc}",
        "-games", str(games), "-repeat", "-concurrency", str(concurrency),
        "-openings", f"file={book.resolve()}", "format=epd", "order=random",
        "-srand", str(seed),
        "-draw", "movenumber=40", "movecount=8", "score=10",
        "-pgnout", str(pgn.resolve()),
    ]
    print(f"RUN {name}: {player} vs {opponent}, {games} games, TC {tc}", flush=True)
    with log.open("w", encoding="utf-8") as writer:
        result = subprocess.run(cmd, stdout=writer, stderr=subprocess.STDOUT, check=False)
    if result.returncode != 0:
        raise RuntimeError(f"{name}: Cute Chess exit {result.returncode}; see {log}")
    stats = analyze_pgn(pgn, player, opponent, expected_games=games)
    print(format_result(name, stats), flush=True)
    return stats


def save(data: dict, directory: Path) -> None:
    directory.mkdir(parents=True, exist_ok=True)
    (directory / "decision.json").write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    lines = [
        "# Stockless history tuning results", "",
        f"Profile: {data['profile']}",
        f"Generated UTC: {data['started_utc']}",
        f"Official book SHA256: {data['book']['source_sha256']}", "",
        "## Screening: candidates vs OFF (exploratory)", "",
        "| Weight | Games | W/D/L | Score | Elo vs OFF | Approx. 95% CI |",
        "|---:|---:|---:|---:|---:|---|",
    ]
    for item in data["screen"]:
        s = item["stats"]
        lines.append(
            f"| {item['weight']} | {s['games']} | "
            f"{s['wins']}/{s['draws']}/{s['losses']} | "
            f"{100*s['score']:.2f}% | {s['elo']} | {s['elo_ci95']} |"
        )
    if data.get("candidate"):
        lines += ["", f"Chosen screening candidate: {data['candidate']['name']}"]
    for k, label in (("confirmation", "Independent confirmation"),
                     ("long_confirmation", "Longer-TC check")):
        if data.get(k):
            lines += ["", f"## {label}", "", format_result(label, data[k])]
    if data.get("stockfish"):
        sf = data["stockfish"]
        lines += ["", "## Stockfish match", "",
                  format_result("OFF vs Stockfish", sf["baseline"])]
        if sf.get("candidate"):
            lines += ["", format_result("Candidate vs Stockfish", sf["candidate"]),
                      "", f"Candidate-minus-OFF score: {sf['difference']}"]
    lines += [
        "", "## Default decision", "",
        f"APPROVED={data['promotion']['approved']}",
        data["promotion"]["reason"], "",
        "CIs are approximate fixed-sample game-level intervals, not clustered-book "
        "or official Fishtest SPRT estimates. See PGN and full logs in Actions artifacts.",
    ]
    report = "\n".join(lines) + "\n"
    (directory / "report.md").write_text(report, encoding="utf-8")
    if os.environ.get("GITHUB_STEP_SUMMARY"):
        with open(os.environ["GITHUB_STEP_SUMMARY"], "a", encoding="utf-8") as fp:
            fp.write(report)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile", choices=("smoke", "full"), default="full")
    parser.add_argument("--cutechess", type=Path, required=True)
    parser.add_argument("--stockless", type=Path, default=Path("build/stockless-src/src/stockless"))
    parser.add_argument("--stockfish", type=Path, default=Path("upstream/stockfish/src/stockfish"))
    parser.add_argument("--books", type=Path, default=Path("results/openings"))
    parser.add_argument("--output", type=Path, default=Path("results/history-tuning"))
    parser.add_argument("--weights", default="50,100,150,200")
    parser.add_argument("--concurrency", type=int, default=2)
    parser.add_argument("--seed", type=int, default=20261017)
    parser.add_argument("--screen-games", type=int, default=0)
    parser.add_argument("--confirm-games", type=int, default=0)
    parser.add_argument("--stockfish-games", type=int, default=0)
    parser.add_argument("--long-games", type=int, default=-1)
    opts = parser.parse_args()
    smoke = opts.profile == "smoke"
    weights = [int(x) for x in opts.weights.split(",")]
    if not weights or len(set(weights)) != len(weights) or any(x < 1 or x > 200 for x in weights):
        parser.error("Weights must be unique integers between 1 and 200")
    if not 1 <= opts.concurrency <= 8:
        parser.error("Concurrency must be 1..8")
    phases = {
        "screen": (opts.screen_games or (8 if smoke else 160), "0.2+0.002"),
        "confirm": (opts.confirm_games or (12 if smoke else 800), "0.4+0.004"),
        "stockfish": (opts.stockfish_games or (12 if smoke else 600), "0.4+0.004"),
        "long": (opts.long_games if opts.long_games >= 0 else (0 if smoke else 400), "1+0.01"),
    }
    for name, (games, _) in phases.items():
        if games % 2 or games < 0 or (name != "long" and games < 2):
            parser.error(f"Invalid game count for {name}: {games}")
    book = json.loads((opts.books / "manifest.json").read_text(encoding="utf-8"))
    if book["profile"] != opts.profile:
        parser.error("Opening book profile does not match tournament profile")
    paths = {n: Path(book["sets"][n]["path"]) for n in ("screen", "confirm", "stockfish")}

    data = {
        "schema": 1,
        "started_utc": datetime.now(timezone.utc).isoformat(),
        "github_run_id": os.environ.get("GITHUB_RUN_ID"),
        "profile": opts.profile,
        "weights": weights,
        "games_requested": {n: g for n, (g, _) in phases.items()},
        "time_controls": {n: tc for n, (_, tc) in phases.items()},
        "options": {"Threads": 1, "Hash": 32, "Aggression": 145,
                    "Overdrive": False, "Threats": True, "Mobile": False},
        "book": book,
        "screen": [],
        "candidate": None,
        "confirmation": None,
        "long_confirmation": None,
        "stockfish": None,
        "promotion": {"approved": False, "weight": None, "reason": "In progress"},
    }

    def play(name: str, weight: int, enabled: bool, opponent: str, stage: str) -> dict:
        player = f"HistoryW{weight:03d}" if enabled else "StocklessOFF"
        return match(
            opts.cutechess, opts.stockless, opts.stockfish, opts.output,
            paths[stage if stage != "long" else "confirm"], name, player,
            weight, enabled, opponent, phases[stage][0], phases[stage][1],
            opts.seed + {"screen": 11, "confirm": 29, "stockfish": 47, "long": 71}[stage],
            opts.concurrency,
        )

    try:
        for weight in weights:
            item = {
                "weight": weight,
                "stats": play(f"screen-{weight:03d}", weight, True, "HistoryOFF", "screen"),
            }
            data["screen"].append(item)
            save(data, opts.output)

        strongest = sorted(data["screen"], key=lambda row: (-row["stats"]["score"], row["weight"]))[0]
        enabled = strongest["stats"]["score"] > 0.5
        weight = strongest["weight"] if enabled else 100
        data["candidate"] = {"name": f"HistoryW{weight:03d}" if enabled else "OFF",
                             "weight": weight, "enabled": enabled}
        if enabled:
            data["confirmation"] = play("confirm-ON-vs-OFF", weight, True, "HistoryOFF", "confirm")
            save(data, opts.output)

        baseline = play("stockfish-OFF", 100, False, "StockfishPinned", "stockfish")
        sf = {"baseline": baseline, "candidate": None, "difference": None}
        if enabled:
            candidate = play("stockfish-best", weight, True, "StockfishPinned", "stockfish")
            sf["candidate"] = candidate
            sf["difference"] = compare_stockfish(candidate, baseline)
        data["stockfish"] = sf
        save(data, opts.output)

        confirmed = enabled and data["confirmation"]["score_ci95"][0] > 0.5
        if confirmed and phases["long"][0]:
            data["long_confirmation"] = play(
                "long-confirm-ON-vs-OFF", weight, True, "HistoryOFF", "long"
            )

        enough = (
            not smoke and phases["confirm"][0] >= 600
            and phases["stockfish"][0] >= 600 and phases["long"][0] >= 400
            and book["book_unique_positions"] >= 2400 and book["sets_disjoint"]
        )
        long_ok = bool(data["long_confirmation"] and
                       data["long_confirmation"]["score_ci95"][0] > 0.5)
        sf_ok = bool(sf["difference"] and sf["difference"]["ci95"][0] > -0.025)
        approved = bool(enough and confirmed and long_ok and sf_ok)
        if not enabled:
            reason = "No ON setting exceeded OFF during screening. Keep default OFF."
        elif smoke:
            reason = "Smoke runs cannot approve a new default."
        elif not confirmed:
            reason = "Independent confirmation could not establish ON > OFF."
        elif not long_ok:
            reason = "Longer time-control holdout inconclusive or negative."
        elif not sf_ok:
            reason = "Candidate could be more than 2.5 score points worse against Stockfish."
        elif not enough:
            reason = "Too few games or insufficiently diverse openings for promotion."
        else:
            reason = (f"Weight {weight} passed independent confirmation, longer-TC "
                      "check, and the Stockfish non-regression guard; eligible "
                      "for experimental branch default.")
        data["promotion"] = {
            "approved": approved, "weight": weight if approved else None,
            "confirmed": bool(confirmed), "long_ok": long_ok,
            "stockfish_not_worse": sf_ok, "reason": reason,
        }
        print("DEFAULT DECISION:", reason, flush=True)
        save(data, opts.output)
    except Exception as error:
        data["promotion"] = {"approved": False, "weight": None,
                             "reason": f"ABORTED: {type(error).__name__}: {error}"}
        save(data, opts.output)
        raise


if __name__ == "__main__":
    main()
