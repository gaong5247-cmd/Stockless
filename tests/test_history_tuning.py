#!/usr/bin/env python3
"""Fast tests for the tuning pipeline; no chess engines required."""
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))

from history_stats import analyze_pgn, compare_stockfish, score_stats
from apply_history_default import apply


class HistoryTuningTests(unittest.TestCase):
    def test_win_draw_loss_and_interval(self):
        stat = score_stats([1.0, 0.5, 0.0, 1.0])
        self.assertEqual((stat["wins"], stat["draws"], stat["losses"]), (2, 1, 1))
        self.assertEqual(stat["score"], 0.625)
        self.assertLess(stat["score_ci95"][0], stat["score"])
        self.assertGreater(stat["score_ci95"][1], stat["score"])

    def test_clear_win_can_pass_confidence(self):
        stat = score_stats([1.0] * 400 + [0.5] * 400)
        self.assertGreater(stat["score_ci95"][0], 0.5)

    def test_equal_draws_are_not_an_improvement(self):
        stat = score_stats([0.5] * 800)
        self.assertEqual(stat["score_ci95"][0], 0.5)

    def test_stockfish_difference(self):
        off = score_stats([0.5] * 100)
        candidate = score_stats([1.0] * 30 + [0.5] * 60 + [0.0] * 10)
        delta = compare_stockfish(candidate, off)
        self.assertAlmostEqual(delta["score_difference"], 0.1)
        self.assertLess(delta["ci95"][0], delta["score_difference"])

    def test_pgn_target_validation_and_strict_game_count(self):
        game = (
            '[Event "Test"]\n[White "HistoryW050"]\n'
            '[Black "HistoryOFF"]\n[Result "1-0"]\n\n1-0\n\n'
            '[Event "Test"]\n[White "HistoryOFF"]\n'
            '[Black "HistoryW050"]\n[Result "0-1"]\n\n0-1\n'
        )
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "match.pgn"
            path.write_text(game, encoding="utf-8")
            stat = analyze_pgn(path, "HistoryW050", "HistoryOFF", 2)
            self.assertEqual(stat["wins"], 2)
            with self.assertRaises(ValueError):
                analyze_pgn(path, "HistoryW050", "HistoryOFF", 4)
            with self.assertRaises(ValueError):
                analyze_pgn(path, "DifferentEngine", "HistoryOFF", 2)

    def test_no_default_mutation_without_approval(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            config = root / "src/stockless/config.h"
            config.parent.mkdir(parents=True)
            config.write_text("unchanged", encoding="utf-8")
            decision = root / "decision.json"
            decision.write_text(json.dumps({
                "promotion": {"approved": False, "reason": "not statistically proven"}
            }), encoding="utf-8")
            self.assertFalse(apply(decision, root))
            self.assertEqual(config.read_text(encoding="utf-8"), "unchanged")


if __name__ == "__main__":
    unittest.main()
