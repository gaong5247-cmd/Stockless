#!/usr/bin/env python3
"""Opt-in Stockless v0.8 candidates vs the frozen Stockless v0.7 binary.

Matches use equal ISA, threads/hash, clock, official paired EPD openings and
disjoint opening books for selection and independent confirmation.
A 200-game screening result is NOT a validated Elo claim.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
from datetime import datetime, timezone
from pathlib import Path

from history_stats import analyze_pgn, format_result

TARGET = 0.55
CANDIDATES = (
    {"name": "HybridOff", "profile": 0, "aggression": 145, "hybrid": False},
    {"name": "Aggression80", "profile": 0, "aggression": 80, "hybrid": True},
    {"name": "Aggression110", "profile": 0, "aggression": 110, "hybrid": True},
    {"name": "Economy", "profile": 1, "aggression": 145, "hybrid": True},
    {"name": "Defense", "profile": 2, "aggression": 145, "hybrid": True},
    {"name": "Balanced", "profile": 3, "aggression": 145, "hybrid": True},
)


def engine(name: str, path: Path, profile: dict | None) -> list[str]:
    args = [
        "-engine", f"name={name}", f"cmd={path.resolve()}", f"dir={path.resolve().parent}",
        "option.Threads=1", "option.Hash=32", "option.MoveOverhead=1",
        "option.StocklessHybrid=true", "option.StocklessAggression=145",
        "option.StocklessThreats=true", "option.StocklessOverdrive=false",
        "option.StocklessMobile=false", "option.StocklessThreatHistory=false",
    ]
    if profile is not None:
        args.extend((
            f"option.StocklessHybrid={'true' if profile['hybrid'] else 'false'}",
            f"option.StocklessAggression={profile['aggression']}",
            f"option.StocklessSearchProfile={profile['profile']}",
        ))
    return args


def play(args: argparse.Namespace, profile: dict, stage: str,
         book: Path, games: int, tc: str, seed: int) -> dict:
    if games <= 0 or games % 2:
        raise ValueError("Game count must be positive and even")
    candidate_name = profile["name"]
    output = args.output / (stage + "-" + candidate_name)
    pgn = output.with_suffix(".pgn")
    log = output.with_suffix(".log")
    cmd = [
        str(args.cutechess.resolve()), "-tournament", "round-robin",
        *engine(candidate_name, args.candidate, profile),
        *engine("StocklessV07", args.baseline, None),
        "-each", "proto=uci", f"tc={tc}",
        "-games", str(games), "-repeat", "-concurrency", str(args.concurrency),
        "-openings", f"file={book.resolve()}", "format=epd",
        "order=random", "-srand", str(seed),
        "-draw", "movenumber=40", "movecount=8", "score=10",
        "-pgnout", str(pgn.resolve()),
    ]
    print(f"RUN {stage}: {candidate_name} vs frozen v0.7, {games} games", flush=True)
    with log.open("w", encoding="utf-8") as stream:
        completed = subprocess.run(cmd, stdout=stream, stderr=subprocess.STDOUT, check=False)
    if completed.returncode:
        raise RuntimeError(f"Cute Chess failed ({completed.returncode}): {log}")
    stats = analyze_pgn(pgn, candidate_name, "StocklessV07", expected_games=games)
    print(format_result(candidate_name, stats), flush=True)
    return stats


def write_report(result: dict, output: Path) -> None:
    (output / "decision.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    lines = [
        "# Stockless v0.8 vs frozen v0.7",
        "",
        f"Run UTC: {result['date']}",
        f"Profile: {result['profile']}",
        f"Baseline: {result['baseline_ref']}",
        f"Target: score STRICTLY above {TARGET:.0%}; 200 games means >110 points.",
        f"Official book SHA256: {result['book']['source_sha256']}",
        "",
        "| Candidate | Games | W/D/L | Score | Approx 95% score CI |",
        "|---|---:|---|---:|---|",
    ]
    for entry in result["screen"]:
        s = entry["stats"]
        lo, hi = s["score_ci95"]
        lines.append(
            f"| {entry['name']} | {s['games']} | "
            f"{s['wins']}/{s['draws']}/{s['losses']} | "
            f"{100*s['score']:.2f}% | [{lo:.3f}, {hi:.3f}] |"
        )
    if result.get("confirmation"):
        s = result["confirmation"]
        lines.extend([
            "",
            "## Disjoint-opening holdout (not used to select the candidate)",
            format_result(result["selected"], s),
            "",
        ])
    lines.extend(["", "## Decision", result["decision"], "",
                  "Selection games cannot validate Elo. The 95% CI is approximate",
                  "and treats games as independent; color-swapped opening pairs",
                  "are correlated, so this is NOT a formal Fishtest SPRT result.",
                  "No script modifies stable defaults or publishes a release.",
                  "Inspect full PGNs and logs for time losses or bad adjudications.",
                  ""])
    report = "\n".join(lines)
    (output / "report.md").write_text(report, encoding="utf-8")
    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary:
        with open(summary, "a", encoding="utf-8") as fp:
            fp.write(report)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile", choices=("smoke", "full"), default="smoke")
    parser.add_argument("--candidate", type=Path, required=True)
    parser.add_argument("--baseline", type=Path, required=True)
    parser.add_argument("--cutechess", type=Path, required=True)
    parser.add_argument("--book-manifest", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=Path("results/v08-strength"))
    parser.add_argument("--concurrency", type=int, default=2)
    parser.add_argument("--screen-games", type=int, default=None)
    parser.add_argument("--confirm-games", type=int, default=None)
    opts = parser.parse_args()

    opts.output.mkdir(parents=True, exist_ok=True)
    for exe in (opts.candidate, opts.baseline, opts.cutechess):
        if not exe.is_file():
            parser.error(f"Missing executable: {exe}")
    if opts.concurrency < 1 or opts.concurrency > 4:
        parser.error("Concurrency must be 1..4")
    smoke = opts.profile == "smoke"
    screen_n = opts.screen_games if opts.screen_games is not None else (12 if smoke else 200)
    confirm_n = opts.confirm_games if opts.confirm_games is not None else (16 if smoke else 800)
    if min(screen_n, confirm_n) < 2 or screen_n % 2 or confirm_n % 2:
        parser.error("Both match counts must be positive and even")

    manifest = json.loads(opts.book_manifest.read_text(encoding="utf-8"))
    if manifest["profile"] != opts.profile or not manifest["sets_disjoint"]:
        parser.error("Opening manifest profile or disjointness mismatch")
    screen_book = Path(manifest["sets"]["screen"]["path"])
    confirm_book = Path(manifest["sets"]["confirm"]["path"])
    if not screen_book.is_file() or not confirm_book.is_file():
        parser.error("Opening files from manifest do not exist")
    if not smoke and (manifest["sets"]["screen"]["positions"] < screen_n // 2
                      or manifest["sets"]["confirm"]["positions"] < confirm_n // 2):
        parser.error("Full test requires unique paired openings for each stage")

    result = {
        "schema": 1, "date": datetime.now(timezone.utc).isoformat(),
        "profile": opts.profile, "baseline_ref": "Stockless_v0.7 / 261d46be",
        "book": manifest, "screen": [], "selected": None,
        "confirmation": None, "approved": False,
        "decision": "In progress", "run_id": os.getenv("GITHUB_RUN_ID"),
    }
    write_report(result, opts.output)

    try:
        for candidate in CANDIDATES:
            stat = play(opts, candidate, "screen", screen_book, screen_n,
                        "0.2+0.002", 20261018)
            result["screen"].append({"name": candidate["name"], "settings": candidate, "stats": stat})
            write_report(result, opts.output)

        selected = max(result["screen"], key=lambda item: (item["stats"]["score"],
                            -CANDIDATES.index(item["settings"])))
        result["selected"] = selected["name"]
        candidate = selected["settings"]
        result["confirmation"] = play(opts, candidate, "confirm", confirm_book, confirm_n,
                                      "0.4+0.004", 20261019)

        conf = result["confirmation"]
        # Strictly observational eligibility: a human reviews the match
        # conditions and independently repeats before changing stable defaults.
        eligible = (not smoke and screen_n >= 200 and confirm_n >= 800
                    and conf["score"] > TARGET and conf["score_ci95"][0] > 0.5)
        result["approved"] = False
        if eligible:
            result["decision"] = (
                f"{candidate['name']} exceeded 55% on the 800-game holdout; "
                "eligible for independent LTC replication and code review, NOT automatic promotion."
            )
        elif smoke:
            result["decision"] = "SMOKE ONLY; UCI integration, clocks and PGN paths checked. No Elo claim."
        else:
            result["decision"] = (
                "55% + positive-confidence holdout gate not met. "
                "Stable defaults remain untouched."
            )
        write_report(result, opts.output)
        print("DECISION:", result["decision"], flush=True)
    except Exception as exc:
        result["decision"] = f"ABORTED: {type(exc).__name__}: {exc}"
        result["approved"] = False
        write_report(result, opts.output)
        raise


if __name__ == "__main__":
    main()
