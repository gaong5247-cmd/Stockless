#!/usr/bin/env python3
"""Validate a predeclared, fixed-sample, color-paired Cute Chess experiment.

Dependency: chess==1.11.2. No result is eligible for promotion until EVERY
planned shard is complete. Repeatedly rerunning a confirmation until it passes
invalidates its interpretation; this tool is not an SPRT implementation.

Run: python tools/paired_match_gate.py --manifest plan.json \
       --results collected --output report

Manifest schema 1:
  {"schema": 1, "mode": "confirmation", "candidate_name": "Candidate",
   "baseline_name": "Baseline", "candidate_sha": "<40 hex>",
   "baseline_sha": "<40 hex>", "stages": [
     {"name": "short", "time_control": "2+0.02", "minimum_games": 4096,
      "min_elo": 5, "shards": [{"directory": "short-0", "games": 512}]},
     {"name": "long", "time_control": "5+0.05", "minimum_games": 1024,
      "min_elo": 0, "shards": [{"directory": "long-0", "games": 256}]}]}
  List ALL shards; the example above is abbreviated. Optional top-level
  candidate_binary_sha256/baseline_binary_sha256 pin already built binaries.
  mode=exploratory permits one stage and can NEVER approve a release.

Each shard directory contains match.pgn, match.log, openings.epd and
metadata.json. Metadata repeats schema, names, commit SHAs, time_control and
games, and records opening_sha256, candidate_binary_sha256,
baseline_binary_sha256, command (argv list), and returncode (must be zero).
The EPD file must have exactly games/2 unique positions. Use -repeat and
-openings format=epd order=sequential with that pre-shuffled file. Both
-games N and -games 2 -rounds N/2 are supported. Do not use -recover.

The report uses color-pair means as observations, reports pentanomial counts,
and transforms a pair-level 95% score interval to logistic Elo. This is an
approximate fixed-sample interval, not a universal engine rating or an
official Fishtest SPRT. In the zero-variance case a bounded Hoeffding interval
replaces the falsely certain normal interval. Promotion requires two or more
distinct time controls, at least 30 pairs per stage, a strictly positive
lower confidence bound, and each stage's predeclared point-Elo threshold.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import statistics
import sys
from collections import Counter
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path

import chess
import chess.pgn

Z95 = statistics.NormalDist().inv_cdf(0.975)
HEX40 = re.compile(r"[0-9a-f]{40}\Z")
HEX64 = re.compile(r"[0-9a-f]{64}\Z")
FAULT = re.compile(
    r"\b(?:illegal\s+move|loses\s+on\s+time|time\s+forfeit|"
    r"stalled\s+connection|connection\s+stalls?|disconnect(?:s|ed|ion)?|"
    r"crash(?:es|ed)?|abandon(?:s|ed)?|segmentation\s+fault|"
    r"failed\s+to\s+(?:start|initialize)|could\s+not\s+(?:start|execute)|"
    r"no\s+response|doesn.t\s+have\s+option|unknown\s+option)\b",
    re.IGNORECASE,
)


class EvidenceError(ValueError):
    """The submitted evidence is incomplete, inconsistent, or invalid."""


def require(condition: bool, message: str) -> None:
    if not condition:
        raise EvidenceError(message)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def normalized_tc(value: str) -> tuple[Decimal, Decimal]:
    match = re.fullmatch(r"(?:0/)?(\d+(?:\.\d+)?)(?:\+(\d+(?:\.\d+)?))?", str(value))
    require(match is not None, f"Unsupported or missing Fischer time control: {value!r}")
    try:
        base, increment = Decimal(match[1]), Decimal(match[2] or "0")
    except InvalidOperation as error:
        raise EvidenceError(f"Invalid time control: {value!r}") from error
    require(base > 0 and increment >= 0, f"Invalid time control: {value!r}")
    return base, increment


def elo(score: float) -> float | str:
    if score <= 0:
        return "-inf"
    if score >= 1:
        return "+inf"
    return 400 * math.log10(score / (1 - score))


def paired_statistics(scores: list[float]) -> dict:
    require(len(scores) >= 2 and len(scores) % 2 == 0, "Complete pairs are required")
    require(all(score in (0.0, 0.5, 1.0) for score in scores), "Invalid game score")
    pairs = [(scores[i] + scores[i + 1]) / 2 for i in range(0, len(scores), 2)]
    n = len(pairs)
    mean = statistics.mean(pairs)
    variance = statistics.variance(pairs) if n > 1 else 0.0
    se = math.sqrt(variance / n)
    if variance == 0 or n == 1:
        margin = math.sqrt(math.log(2 / 0.05) / (2 * n))
        method = "pair-level bounded Hoeffding 95% CI (zero-variance fallback)"
    else:
        margin = Z95 * se
        method = "fixed-sample pair-cluster 95% normal CI (approximate)"
    low, high = max(0.0, mean - margin), min(1.0, mean + margin)
    return {
        "games": len(scores), "pairs": n,
        "wins": scores.count(1.0), "draws": scores.count(0.5), "losses": scores.count(0.0),
        "pentanomial": [pairs.count(value) for value in (0.0, 0.25, 0.5, 0.75, 1.0)],
        "score": mean, "pair_sample_variance": variance, "score_se": se,
        "score_ci95": [low, high], "elo": elo(mean), "elo_ci95": [elo(low), elo(high)],
        "method": method,
    }


class CheckedGameBuilder(chess.pgn.GameBuilder):
    """Reject truncated PGNs whose Result header outlives their movetext."""

    def begin_game(self) -> None:
        super().begin_game()
        self.result_tokens: list[str] = []

    def visit_result(self, result: str) -> None:
        self.result_tokens.append(result)
        super().visit_result(result)

    def result(self) -> chess.pgn.Game:
        game = super().result()
        game.result_tokens = self.result_tokens
        return game


def load_openings(path: Path, expected_pairs: int) -> list[chess.Board]:
    boards = []
    for line_number, text in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        text = text.strip()
        if not text or text.startswith("#"):
            continue
        board = chess.Board()
        try:
            board.set_epd(text)
        except ValueError as error:
            raise EvidenceError(f"{path}:{line_number}: invalid EPD: {error}") from error
        require(board.is_valid(), f"{path}:{line_number}: illegal opening position")
        boards.append(board)
    require(len(boards) == expected_pairs,
            f"{path}: expected {expected_pairs} opening positions, found {len(boards)}")
    return boards


def opening_key(board: chess.Board) -> str:
    # Ignore irrelevant EP squares for identity; preserve move clocks separately
    # when checking that a game really starts from its declared EPD position.
    return " ".join(board.fen(en_passant="legal").split()[:4])


def validate_command(command: list[str], metadata: dict) -> None:
    require(isinstance(command, list) and bool(command)
            and all(isinstance(item, str) for item in command), "command must be an argv list")
    groups: list[tuple[str, list[str]]] = []
    for argument in command[1:]:
        if argument.startswith("-"):
            groups.append((argument, []))
        else:
            require(bool(groups), "Malformed Cute Chess command")
            groups[-1][1].append(argument)
    grouped: dict[str, list[list[str]]] = {}
    for option, values in groups:
        grouped.setdefault(option, []).append(values)
    require("-recover" not in grouped, "Recovery mode can hide engine faults")

    def singleton(option: str, default: list[str] | None = None) -> list[str]:
        values = grouped.get(option)
        if values is None and default is not None:
            return default
        require(values is not None and len(values) == 1, f"Expected exactly one {option}")
        return values[0]

    def keyvalues(items: list[str]) -> dict[str, str]:
        values = {}
        for item in items:
            require("=" in item, f"Expected key=value command item: {item!r}")
            key, value = item.split("=", 1)
            require(key not in values, f"Duplicate command setting: {key}")
            values[key] = value
        return values

    repeat = singleton("-repeat")
    require(repeat in ([], ["2"]), "Each opening must be repeated exactly twice")
    games, rounds = singleton("-games"), singleton("-rounds", ["1"])
    require(len(games) == len(rounds) == 1 and games[0].isdigit() and rounds[0].isdigit(),
            "Invalid -games/-rounds command")
    require(int(games[0]) > 0 and int(rounds[0]) > 0
            and int(games[0]) * int(rounds[0]) == metadata["games"],
            "Command game count differs from fixed plan")
    require(singleton("-tournament", ["round-robin"]) in (["round-robin"], ["gauntlet"]),
            "Only two-engine round-robin/gauntlet matches are supported")
    require("-noswap" not in grouped and "-sprt" not in grouped,
            "Fixed-sample color-paired matches cannot disable swapping or stop by SPRT")
    each = keyvalues(singleton("-each"))
    require(each.get("proto") == "uci", "Expected UCI protocol")
    require(normalized_tc(each.get("tc")) == normalized_tc(metadata["time_control"]),
            "Command time control differs from fixed plan")
    openings = keyvalues(singleton("-openings"))
    require(openings.get("format") == "epd" and openings.get("order") == "sequential",
            "Use the exact sequential EPD shard (pre-shuffle it before running)")
    require(bool(openings.get("file")), "Missing opening-file command option")
    engines = [keyvalues(items) for items in grouped.get("-engine", [])]
    names = {metadata["candidate_name"], metadata["baseline_name"]}
    require(len(engines) == 2 and {item.get("name") for item in engines} == names,
            "Command must contain exactly the planned two engines")
    effective_engines = [{**each, **engine} for engine in engines]
    require(all(engine.get("option.Threads") == "1" for engine in effective_engines),
            "Both engines must explicitly use one search thread")
    require(all(normalized_tc(engine.get("tc")) == normalized_tc(metadata["time_control"])
                for engine in effective_engines), "Per-engine time control differs from fixed plan")
    hashes = [engine.get("option.Hash") for engine in effective_engines]
    require(hashes[0] == hashes[1] and bool(hashes[0]) and hashes[0].isdigit()
            and int(hashes[0]) > 0, "Both engines must use the same explicit hash size")
    require(all(bool(engine.get("cmd")) for engine in engines), "Missing engine command")


def analyze_shard(directory: Path, plan: dict, stage: dict, games: int) -> tuple[dict, list[float], list[str]]:
    paths = {name: directory / name for name in ("match.pgn", "match.log", "openings.epd", "metadata.json")}
    require(all(path.is_file() for path in paths.values()), f"Missing evidence in {directory}")
    metadata = json.loads(paths["metadata.json"].read_text(encoding="utf-8"))
    require(metadata.get("schema") == 1, f"{directory}: unsupported metadata schema")
    for name in ("candidate_name", "baseline_name", "candidate_sha", "baseline_sha"):
        require(metadata.get(name) == plan[name], f"{directory}: mismatched {name}")
    for name in ("candidate_build_profile", "baseline_build_profile"):
        if name in plan:
            require(metadata.get(name) == plan[name], f"{directory}: mismatched {name}")
    require(type(metadata.get("returncode")) is int and metadata["returncode"] == 0,
            f"{directory}: Cute Chess did not exit successfully")
    require(type(metadata.get("games")) is int and metadata["games"] == games,
            f"{directory}: metadata game count differs from fixed plan")
    require(normalized_tc(metadata.get("time_control")) == normalized_tc(stage["time_control"]),
            f"{directory}: metadata time control differs from fixed plan")
    require(metadata.get("opening_sha256") == sha256(paths["openings.epd"]),
            f"{directory}: opening file hash does not match recorded run")
    for name in ("candidate_binary_sha256", "baseline_binary_sha256"):
        require(isinstance(metadata.get(name), str) and HEX64.fullmatch(metadata[name]) is not None,
                f"{directory}: missing or malformed {name}")
    validate_command(metadata.get("command"), metadata)
    log = paths["match.log"].read_text(encoding="utf-8", errors="strict")
    fault = FAULT.search(log)
    require(fault is None, f"{directory}: engine/arena fault in log: {fault[0] if fault else ''}")
    require(re.search(r"^Finished match\s*$", log, re.MULTILINE) is not None,
            f"{directory}: Cute Chess completion marker is missing")
    openings = load_openings(paths["openings.epd"], games // 2)
    scores: list[float] = []
    colors: list[str] = []
    terminations: Counter = Counter()
    with paths["match.pgn"].open(encoding="utf-8", errors="strict") as stream:
        while game := chess.pgn.read_game(stream, Visitor=CheckedGameBuilder):
            index = len(scores)
            require(index < games, f"{directory}: more PGN games than planned")
            require(not game.errors, f"{directory}: illegal/malformed PGN game {index + 1}")
            result = game.headers.get("Result")
            require(result in ("1-0", "0-1", "1/2-1/2"),
                    f"{directory}: unfinished game {index + 1}")
            require(game.result_tokens == [result],
                    f"{directory}: missing/inconsistent movetext result in game {index + 1}")
            white, black = game.headers.get("White"), game.headers.get("Black")
            require({white, black} == {plan["candidate_name"], plan["baseline_name"]},
                    f"{directory}: unexpected opponents in game {index + 1}")
            require(normalized_tc(game.headers.get("TimeControl")) == normalized_tc(stage["time_control"]),
                    f"{directory}: PGN time control differs in game {index + 1}")
            termination = game.headers.get("Termination", "normal").lower()
            require(termination in ("normal", "adjudication"),
                    f"{directory}: unacceptable termination {termination!r} in game {index + 1}")
            terminations[termination] += 1
            require(game.board().fen(en_passant="legal") == openings[index // 2].fen(en_passant="legal"),
                    f"{directory}: wrong opening/clock in game {index + 1}")
            for node in (game, *game.mainline()):
                require(FAULT.search(node.comment or "") is None,
                        f"{directory}: engine fault in PGN comment, game {index + 1}")
            color = "white" if white == plan["candidate_name"] else "black"
            if index % 2:
                require(colors[-1] != color, f"{directory}: pair {index // 2 + 1} did not swap colors")
            colors.append(color)
            scores.append(0.5 if result == "1/2-1/2" else
                          float((result == "1-0") == (color == "white")))
    require(len(scores) == games, f"{directory}: expected {games} finished games, found {len(scores)}")
    return ({
        "directory": str(directory), "games": games, "time_control": stage["time_control"],
        "candidate_binary_sha256": metadata["candidate_binary_sha256"],
        "baseline_binary_sha256": metadata["baseline_binary_sha256"],
        "termination_counts": dict(terminations),
        "files_sha256": {name: sha256(path) for name, path in paths.items()},
        "command": metadata["command"],
    }, scores, [opening_key(board) for board in openings])


def analyze_experiment(plan: dict, results: Path) -> dict:
    require(plan.get("schema") == 1, "Unsupported manifest schema")
    require(plan.get("mode") in ("exploratory", "confirmation"), "Invalid experiment mode")
    for name in ("candidate_name", "baseline_name"):
        require(isinstance(plan.get(name), str) and bool(plan[name]), f"Missing {name}")
    require(plan["candidate_name"] != plan["baseline_name"], "Engine names must differ")
    for name in ("candidate_sha", "baseline_sha"):
        require(isinstance(plan.get(name), str) and HEX40.fullmatch(plan[name]) is not None,
                f"Missing or malformed {name}")
    require(isinstance(plan.get("stages"), list) and bool(plan["stages"]), "No planned stages")
    seen_directories: set[Path] = set()
    seen_positions: set[str] = set()
    stage_names: set[str] = set()
    time_controls: set[tuple] = set()
    pinned_hashes = {name: plan.get(name) for name in ("candidate_binary_sha256", "baseline_binary_sha256")}
    report = {"schema": 1, "valid": True, "approved": False, "mode": plan["mode"],
              "candidate_name": plan["candidate_name"], "baseline_name": plan["baseline_name"],
              "candidate_sha": plan["candidate_sha"], "baseline_sha": plan["baseline_sha"],
              "generated_utc": datetime.now(timezone.utc).isoformat(), "stages": []}
    for name in ("candidate_build_profile", "baseline_build_profile"):
        if name in plan:
            report[name] = plan[name]
    for stage in plan["stages"]:
        name = stage.get("name")
        require(isinstance(name, str) and bool(name) and name not in stage_names, "Stage names must be unique")
        stage_names.add(name)
        time_controls.add(normalized_tc(stage.get("time_control")))
        minimum, threshold = stage.get("minimum_games"), stage.get("min_elo", 5.0)
        require(type(minimum) is int and minimum >= 2 and minimum % 2 == 0,
                f"{name}: minimum_games must be a positive even integer")
        require(type(threshold) in (int, float) and math.isfinite(threshold) and threshold >= 0,
                f"{name}: min_elo must be finite and nonnegative")
        require(isinstance(stage.get("shards"), list) and bool(stage["shards"]), f"{name}: no planned shards")
        scores: list[float] = []
        shard_reports = []
        for shard in stage["shards"]:
            relative = Path(shard["directory"])
            directory = (results / relative).resolve()
            require(not relative.is_absolute() and directory.is_relative_to(results.resolve()),
                    "Shard directory must be inside the results directory")
            require(directory not in seen_directories, f"Duplicate shard: {relative}")
            seen_directories.add(directory)
            games = shard.get("games")
            require(type(games) is int and games >= 2 and games % 2 == 0,
                    f"{relative}: games must be a positive even integer")
            item, shard_scores, positions = analyze_shard(directory, plan, stage, games)
            for position in positions:
                require(position not in seen_positions,
                        f"Repeated opening across shards/stages: {position}")
                seen_positions.add(position)
            for key in pinned_hashes:
                if pinned_hashes[key] is None:
                    pinned_hashes[key] = item[key]
                require(item[key] == pinned_hashes[key], f"Binary changed between shards: {key}")
            scores.extend(shard_scores)
            shard_reports.append(item)
        require(len(scores) >= minimum, f"{name}: planned total below minimum_games")
        stats = paired_statistics(scores)
        point_ok = stats["elo"] == "+inf" or (isinstance(stats["elo"], (int, float)) and stats["elo"] >= threshold)
        passed = stats["pairs"] >= 30 and stats["score_ci95"][0] > 0.5 and point_ok
        report["stages"].append({"name": name, "time_control": stage["time_control"],
                                 "minimum_games": minimum, "min_elo": threshold,
                                 "passed": passed, "statistics": stats, "shards": shard_reports})
    is_confirmation = plan["mode"] == "confirmation"
    if is_confirmation:
        require(len(time_controls) >= 2, "Confirmation needs at least two distinct time controls")
    report.update(pinned_hashes)
    report["approved"] = bool(is_confirmation and all(stage["passed"] for stage in report["stages"]))
    report["unique_openings"] = len(seen_positions)
    report["reason"] = ("All predeclared paired confirmation stages passed."
                        if report["approved"] else
                        "Exploratory experiments cannot approve a release."
                        if not is_confirmation else
                        "At least one predeclared confirmation stage is inconclusive or below its threshold.")
    report["limitations"] = (
        "Fixed-sample pair-level confidence intervals; not SPRT. Do not rerun until favorable. "
        "Openings are distinct within this experiment; independence from screening must be recorded in its plan. "
        "Recorded process metadata and binary hashes are provenance supplied by the runner, not a signature. "
        "Results apply to these opponents, time controls, compiler, CPU and options."
    )
    return report


def text_elo(value: float | str) -> str:
    return f"{value:+.2f}" if isinstance(value, (float, int)) else value


def markdown_report(report: dict) -> str:
    lines = ["# Stockless paired strength gate", "",
             f"Valid evidence: **{report['valid']}**", f"Release approved: **{report['approved']}**", "",
             report.get("reason", report.get("error", "")), ""]
    if report.get("valid"):
        lines += [f"Candidate: `{report['candidate_sha']}`", f"Baseline: `{report['baseline_sha']}`", "",
                  "| Stage | TC | Games | W/D/L | Score | Elo | Pair 95% Elo interval | Pass |",
                  "|---|---|---:|---|---:|---:|---|---|"]
        if "candidate_build_profile" in report:
            lines[7:7] = [f"Build profiles: `{report['candidate_build_profile']}` versus "
                           f"`{report['baseline_build_profile']}`.", ""]
        for stage in report["stages"]:
            stat = stage["statistics"]
            low, high = map(text_elo, stat["elo_ci95"])
            lines.append(f"| {stage['name']} | {stage['time_control']} | {stat['games']} | "
                         f"{stat['wins']}/{stat['draws']}/{stat['losses']} | {100*stat['score']:.3f}% | "
                         f"{text_elo(stat['elo'])} | [{low}, {high}] | {stage['passed']} |")
        lines += ["", "## Statistical method", "", report["limitations"], ""]
        for stage in report["stages"]:
            stat = stage["statistics"]
            lines += [f"- {stage['name']}: {stat['pairs']} pairs; pentanomial {stat['pentanomial']}; "
                      f"{stat['method']}; point-Elo threshold {stage['min_elo']:+.2f}."]
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--results", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--require-pass", action="store_true", help="Also exit nonzero on valid but inconclusive results")
    arguments = parser.parse_args()
    try:
        plan = json.loads(arguments.manifest.read_text(encoding="utf-8"))
        report = analyze_experiment(plan, arguments.results)
        report["manifest_sha256"] = sha256(arguments.manifest)
    except (EvidenceError, OSError, ValueError, KeyError, TypeError) as error:
        report = {"schema": 1, "valid": False, "approved": False,
                  "error": f"{type(error).__name__}: {error}"}
    arguments.output.mkdir(parents=True, exist_ok=True)
    (arguments.output / "report.json").write_text(json.dumps(report, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    (arguments.output / "report.md").write_text(markdown_report(report), encoding="utf-8")
    print(markdown_report(report))
    return 0 if report["valid"] and (report["approved"] or not arguments.require_pass) else 1


if __name__ == "__main__":
    sys.exit(main())
