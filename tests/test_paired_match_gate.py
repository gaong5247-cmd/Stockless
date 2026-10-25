#!/usr/bin/env python3
"""Evidence-level regressions for the fixed-sample paired strength gate."""
from __future__ import annotations

import copy
import json
import math
from pathlib import Path
import random
import sys
import tempfile
import unittest

import chess
import chess.pgn

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from paired_match_gate import (  # noqa: E402
    EvidenceError, Z95, analyze_experiment, opening_key, paired_statistics, sha256,
)


def unique_openings(count: int, seed: int = 1) -> list[chess.Board]:
    rng = random.Random(seed)
    positions = {}
    while len(positions) < count:
        board = chess.Board()
        for _ in range(12):
            if board.is_game_over():
                break
            board.push(rng.choice(list(board.legal_moves)))
        if not board.is_game_over():
            reset = chess.Board()
            reset.set_epd(board.epd(en_passant="legal"))
            positions.setdefault(opening_key(reset), reset)
    return list(positions.values())


def plan_for(mode: str = "exploratory", games: int = 4) -> dict:
    return {
        "schema": 1, "mode": mode, "candidate_name": "Candidate", "baseline_name": "Baseline",
        "candidate_sha": "a" * 40, "baseline_sha": "b" * 40,
        "stages": [{"name": "short", "time_control": "2+0.02", "minimum_games": games,
                    "min_elo": 5.0, "shards": [{"directory": "short-0", "games": games}]}],
    }


def write_shard(root: Path, plan: dict, stage_index: int, scores: list[float], seed: int = 1) -> Path:
    stage = plan["stages"][stage_index]
    directory = root / stage["shards"][0]["directory"]
    directory.mkdir(parents=True)
    boards = unique_openings(len(scores) // 2, seed)
    book = directory / "openings.epd"
    book.write_text("\n".join(board.epd(en_passant="legal") for board in boards) + "\n")
    pgns = []
    for index, score in enumerate(scores):
        game = chess.pgn.Game()
        game.setup(boards[index // 2])
        game.headers["White"] = "Candidate" if index % 2 == 0 else "Baseline"
        game.headers["Black"] = "Baseline" if index % 2 == 0 else "Candidate"
        game.headers["Round"] = str(index // 2 + 1)
        game.headers["TimeControl"] = stage["time_control"]
        game.headers["Termination"] = "adjudication"
        game.headers["Result"] = ("1/2-1/2" if score == 0.5 else
                                   "1-0" if (score == 1) == (index % 2 == 0) else "0-1")
        game.add_main_variation(next(iter(boards[index // 2].legal_moves)))
        pgns.append(str(game))
    (directory / "match.pgn").write_text("\n\n".join(pgns) + "\n")
    (directory / "match.log").write_text("Finished match\n")
    command = [
        "/bin/cutechess-cli", "-engine", "name=Candidate", "cmd=/bin/candidate",
        "-engine", "name=Baseline", "cmd=/bin/baseline",
        "-each", "proto=uci", f"tc={stage['time_control']}", "option.Threads=1", "option.Hash=32",
        "-tournament", "gauntlet", "-rounds", str(len(scores) // 2), "-games", "2",
        "-repeat", "-openings", f"file={book}", "format=epd", "order=sequential",
        "-pgnout", str(directory / "match.pgn"),
    ]
    metadata = {
        **{key: plan[key] for key in ("schema", "candidate_name", "baseline_name", "candidate_sha", "baseline_sha")},
        "time_control": stage["time_control"], "games": len(scores), "opening_sha256": sha256(book),
        "candidate_binary_sha256": "c" * 64, "baseline_binary_sha256": "d" * 64,
        "command": command, "returncode": 0,
    }
    (directory / "metadata.json").write_text(json.dumps(metadata))
    return directory


def change_metadata(directory: Path, **changes: object) -> None:
    path = directory / "metadata.json"
    value = json.loads(path.read_text())
    value.update(changes)
    path.write_text(json.dumps(value))


class PairStatisticsTests(unittest.TestCase):
    def test_pairs_are_observations_not_individual_games(self) -> None:
        # Pair totals: 2, 0, 1. Mean per game=.5; pair sample variance=.25.
        stat = paired_statistics([1, 1, 0, 0, 1, 0])
        self.assertEqual(stat["pentanomial"], [1, 0, 1, 0, 1])
        self.assertAlmostEqual(stat["pair_sample_variance"], 0.25)
        self.assertAlmostEqual(stat["score_se"], math.sqrt(0.25 / 3))
        self.assertEqual(stat["score_ci95"], [0, 1])

    def test_interval_and_elo_transform(self) -> None:
        scores = [1, 1, 1, 0.5, 0.5, 0.5, 0.5, 0] * 50
        stat = paired_statistics(scores)
        low = stat["score"] - Z95 * stat["score_se"]
        self.assertAlmostEqual(stat["score_ci95"][0], low)
        self.assertAlmostEqual(stat["elo_ci95"][0], 400 * math.log10(low / (1 - low)))
        self.assertEqual(stat["pentanomial"], [0, 50, 50, 50, 50])

    def test_all_identical_pairs_do_not_have_false_certainty(self) -> None:
        stat = paired_statistics([1, 0] * 100)
        self.assertEqual(stat["score"], 0.5)
        self.assertLess(stat["score_ci95"][0], 0.5)
        self.assertGreater(stat["score_ci95"][1], 0.5)
        self.assertIn("Hoeffding", stat["method"])
        self.assertLess(paired_statistics([1, 1] * 100)["score_ci95"][0], 1)


class EvidenceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.plan = plan_for()
        self.directory = write_shard(self.root, self.plan, 0, [1, 0.5, 0.5, 0])

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def test_complete_exploratory_evidence_never_promotes(self) -> None:
        report = analyze_experiment(self.plan, self.root)
        self.assertTrue(report["valid"])
        self.assertFalse(report["approved"])
        self.assertEqual(report["stages"][0]["statistics"]["games"], 4)
        self.assertEqual(report["stages"][0]["statistics"]["score"], 0.5)
        self.assertEqual(report["unique_openings"], 2)

    def test_missing_planned_shard_is_invalid_even_when_finished_shard_wins(self) -> None:
        self.plan["stages"][0]["shards"].append({"directory": "short-1", "games": 4})
        with self.assertRaisesRegex(EvidenceError, "Missing evidence"):
            analyze_experiment(self.plan, self.root)

    def test_truncated_movetext_is_not_a_completed_game(self) -> None:
        path = self.directory / "match.pgn"
        content = path.read_text().rstrip()
        self.assertTrue(content.endswith("1-0"))
        path.write_text(content[:-3] + "\n")
        with self.assertRaisesRegex(EvidenceError, "movetext result"):
            analyze_experiment(self.plan, self.root)

    def test_same_color_pair_is_invalid(self) -> None:
        path = self.directory / "match.pgn"
        content = path.read_text().replace('[White "Baseline"]\n[Black "Candidate"]',
                                           '[White "Candidate"]\n[Black "Baseline"]', 1)
        path.write_text(content)
        with self.assertRaisesRegex(EvidenceError, "did not swap colors"):
            analyze_experiment(self.plan, self.root)

    def test_different_opening_inside_pair_is_invalid(self) -> None:
        path = self.directory / "openings.epd"
        lines = path.read_text().splitlines()
        path.write_text("\n".join(reversed(lines)) + "\n")
        change_metadata(self.directory, opening_sha256=sha256(path))
        with self.assertRaisesRegex(EvidenceError, "wrong opening"):
            analyze_experiment(self.plan, self.root)

    def test_faults_in_log_are_invalid(self) -> None:
        for message in ("Candidate disconnects", "White loses on time", "Candidate makes an illegal move"):
            with self.subTest(message=message):
                (self.directory / "match.log").write_text(message + "\nFinished match\n")
                with self.assertRaisesRegex(EvidenceError, "fault in log"):
                    analyze_experiment(self.plan, self.root)

    def test_time_forfeit_header_is_invalid_even_with_clean_log(self) -> None:
        path = self.directory / "match.pgn"
        path.write_text(path.read_text().replace('[Termination "adjudication"]', '[Termination "time forfeit"]', 1))
        with self.assertRaisesRegex(EvidenceError, "unacceptable termination"):
            analyze_experiment(self.plan, self.root)

    def test_hash_mismatch_and_failed_process_are_invalid(self) -> None:
        change_metadata(self.directory, returncode=1)
        with self.assertRaisesRegex(EvidenceError, "did not exit successfully"):
            analyze_experiment(self.plan, self.root)
        change_metadata(self.directory, returncode=0, opening_sha256="f" * 64)
        with self.assertRaisesRegex(EvidenceError, "opening file hash"):
            analyze_experiment(self.plan, self.root)

    def test_unexpected_game_count_cannot_be_summarized_as_success(self) -> None:
        path = self.directory / "match.pgn"
        with path.open("a") as stream:
            stream.write("\n" + path.read_text())
        with self.assertRaisesRegex(EvidenceError, "more PGN games than planned"):
            analyze_experiment(self.plan, self.root)

    def test_command_cannot_enable_recovery_or_override_only_one_hash(self) -> None:
        path = self.directory / "metadata.json"
        metadata = json.loads(path.read_text())
        command = metadata["command"] + ["-recover"]
        change_metadata(self.directory, command=command)
        with self.assertRaisesRegex(EvidenceError, "Recovery mode"):
            analyze_experiment(self.plan, self.root)
        command = metadata["command"].copy()
        command.insert(command.index("cmd=/bin/candidate") + 1, "option.Hash=64")
        change_metadata(self.directory, command=command)
        with self.assertRaisesRegex(EvidenceError, "same explicit hash"):
            analyze_experiment(self.plan, self.root)


class ConfirmationTests(unittest.TestCase):
    def test_two_positive_stages_approve_but_negative_or_changed_binary_does_not(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            plan = plan_for("confirmation", games=64)
            plan["stages"].append({"name": "long", "time_control": "5+0.05", "minimum_games": 64,
                                   "min_elo": 0.0, "shards": [{"directory": "long-0", "games": 64}]})
            write_shard(root, plan, 0, [1, 1] * 32, seed=10)
            long = write_shard(root, plan, 1, [1, 1] * 32, seed=20)
            report = analyze_experiment(plan, root)
            self.assertTrue(report["approved"])
            self.assertEqual(report["unique_openings"], 64)
            change_metadata(long, candidate_binary_sha256="e" * 64)
            with self.assertRaisesRegex(EvidenceError, "Binary changed"):
                analyze_experiment(plan, root)
            change_metadata(long, candidate_binary_sha256="c" * 64)
            # A complete but drawn long stage must leave promotion false.
            pgn = long / "match.pgn"
            content = pgn.read_text().replace('"1-0"', '"1/2-1/2"').replace('"0-1"', '"1/2-1/2"')
            content = content.replace(" 1-0\n", " 1/2-1/2\n").replace(" 0-1\n", " 1/2-1/2\n")
            pgn.write_text(content)
            self.assertFalse(analyze_experiment(plan, root)["approved"])

    def test_duplicate_positions_across_stages_are_invalid(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            plan = plan_for("confirmation")
            long = copy.deepcopy(plan["stages"][0])
            long.update(name="long", time_control="5+0.05", shards=[{"directory": "long-0", "games": 4}])
            plan["stages"].append(long)
            write_shard(root, plan, 0, [1, 1, 1, 1], seed=2)
            write_shard(root, plan, 1, [1, 1, 1, 1], seed=2)
            with self.assertRaisesRegex(EvidenceError, "Repeated opening"):
                analyze_experiment(plan, root)


if __name__ == "__main__":
    unittest.main()
