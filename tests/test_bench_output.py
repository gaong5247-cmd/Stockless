"""Regression checks for complete, position-by-position bench comparisons."""
from __future__ import annotations

import contextlib
import io
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from bench_output import default_bench_position_count, parse_bench
import compare_bench
import compare_lean_policy_profiles


# Same framing as the pinned uci.cpp: position header, full search info (or
# depth-zero mate/stalemate info), one bestmove, then three summary counters.
COMPLETE = """Stockless test fixture
Position: 1/3 (rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1)
info string Using NNUE test fixture
info depth 1 seldepth 2 multipv 1 score cp 12 nodes 10 nps 10000 hashfull 0 tbhits 0 time 1 pv e2e4
info depth 2 currmove e2e4 currmovenumber 1
info depth 2 seldepth 3 multipv 1 score cp 15 nodes 100 nps 10000 hashfull 0 tbhits 0 time 10 pv e2e4 e7e5
bestmove e2e4 ponder e7e5

Position: 2/3 (8/8/8/8/8/6k1/6p1/6K1 w - - 0 1)
info depth 0 score mate 0
bestmove (none)

Position: 3/3 (rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1)
info depth 2 seldepth 4 multipv 1 score cp 21 nodes 200 nps 10000 hashfull 0 tbhits 0 time 20 pv d2d4 d7d5
bestmove d2d4 ponder d7d5

===========================
Total time (ms) : 20
Nodes searched  : 300
Nodes/second    : 15000
"""


def parse(output: str = COMPLETE):
    return parse_bench(output, expected_positions=3, depth=2)


class BenchOutputTests(unittest.TestCase):
    def test_complete_searches_include_terminal_positions(self) -> None:
        result = parse()
        self.assertEqual(result.nodes, 300)
        self.assertEqual(result.nps, 15000)
        self.assertEqual([position.nodes for position in result.positions], [100, 0, 200])
        self.assertEqual(result.positions[1].bestmove, "(none)")
        self.assertEqual(result.positions[0].pv, ("e2e4", "e7e5"))

    def test_empty_partial_and_duplicate_bestmoves_are_rejected(self) -> None:
        cases = {
            "none": "\n".join(line for line in COMPLETE.splitlines() if not line.startswith("bestmove")),
            "partial": COMPLETE.replace("bestmove d2d4 ponder d7d5\n", ""),
            "duplicate": COMPLETE.replace("bestmove (none)", "bestmove (none)\nbestmove (none)"),
            "malformed": COMPLETE.replace("bestmove e2e4 ponder e7e5", "bestmove invalid"),
        }
        for name, output in cases.items():
            with self.subTest(name=name), self.assertRaises(ValueError):
                parse(output)

    def test_full_position_count_is_required_even_with_valid_looking_summary(self) -> None:
        for output in (
            COMPLETE[COMPLETE.index("Total time"):],
            COMPLETE.replace("/3 (", "/2 ("),
            COMPLETE.replace("Position: 2/3", "Position: 1/3"),
            COMPLETE[:COMPLETE.index("Position: 3/3")] + COMPLETE[COMPLETE.index("Total time"):],
        ):
            with self.subTest(output=output[-100:]), self.assertRaises(ValueError):
                parse(output)

    def test_missing_info_unfinished_depth_and_inconsistent_pv_are_rejected(self) -> None:
        for output in (
            "\n".join(line for line in COMPLETE.splitlines() if not line.startswith("info depth")),
            COMPLETE.replace("info depth 2 seldepth 4", "info depth 1 seldepth 4"),
            COMPLETE.replace("bestmove d2d4 ponder d7d5", "bestmove d2d4 ponder e7e5"),
            COMPLETE.replace("bestmove d2d4 ponder d7d5", "bestmove e2e4 ponder d7d5"),
            COMPLETE.replace("bestmove (none)", "bestmove h1h2"),
        ):
            with self.subTest(output=output[-100:]), self.assertRaises(ValueError):
                parse(output)

    def test_summary_must_be_complete_unique_and_match_position_nodes(self) -> None:
        for output in (
            COMPLETE.replace("Nodes searched  : 300", "Nodes searched  : 301"),
            COMPLETE.replace("Nodes/second    : 15000", "Nodes/second    : 1"),
            COMPLETE.replace("Total time (ms) : 20\n", ""),
            COMPLETE.replace("Nodes/second    : 15000\n", ""),
            COMPLETE + "Nodes searched : 300\n",
        ):
            with self.subTest(output=output[-100:]), self.assertRaises(ValueError):
                parse(output)

    def test_score_pv_and_node_distribution_are_part_of_signature(self) -> None:
        baseline = parse()
        for changed in (
            COMPLETE.replace("nodes 100 ", "nodes 101 ").replace("nodes 200 ", "nodes 199 "),
            COMPLETE.replace("score cp 21", "score cp 22"),
            COMPLETE.replace("pv d2d4 d7d5", "pv d2d4 d7d5 c2c4"),
        ):
            candidate = parse(changed)
            self.assertEqual(candidate.nodes, baseline.nodes)
            self.assertEqual([p.bestmove for p in candidate.positions], [p.bestmove for p in baseline.positions])
            self.assertNotEqual(candidate.positions, baseline.positions)

    def test_pinned_suite_count_excludes_option_commands(self) -> None:
        source = '''const std::vector<std::string> Defaults = {
          "setoption name UCI_Chess960 value false",
          "8/8/8/8/8/6k1/6p1/6K1 w - -",
          "setoption name UCI_Chess960 value true",
          "7k/7P/6K1/8/3B4/8/8/8 b - -",
        };'''
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "benchmark.cpp"
            path.write_text(source, encoding="utf-8")
            self.assertEqual(default_bench_position_count(path), 2)
            path.write_text("const int no_suite = 0;", encoding="utf-8")
            with self.assertRaises(ValueError):
                default_bench_position_count(path)

    def test_both_comparison_tools_reject_an_identically_incomplete_engine(self) -> None:
        broken = "\n".join(line for line in COMPLETE.splitlines() if not line.startswith("bestmove"))
        process = subprocess.CompletedProcess([], 0, stdout=broken)
        for module in (compare_bench, compare_lean_policy_profiles):
            with self.subTest(module=module.__name__), \
                    mock.patch.object(module.subprocess, "run", return_value=process), \
                    mock.patch.object(module, "default_bench_position_count", return_value=3):
                with self.assertRaises((ValueError, RuntimeError)):
                    if module is compare_bench:
                        module.bench(Path("fixture"), 2, 5)
                    else:
                        module.bench(Path("fixture"), {}, 2, 5)

    def test_both_comparisons_reject_equal_total_with_changed_position_nodes(self) -> None:
        baseline = parse()
        candidate = parse(COMPLETE.replace("nodes 100 ", "nodes 101 ").replace("nodes 200 ", "nodes 199 "))
        with tempfile.TemporaryDirectory() as directory:
            binary = Path(directory) / "fixture"
            binary.touch()
            for module in (compare_bench, compare_lean_policy_profiles):
                argv = [module.__file__, str(binary), str(binary)]
                if module is compare_bench:
                    argv += ["--rounds", "1"]
                with self.subTest(module=module.__name__), \
                        mock.patch.object(sys, "argv", argv), \
                        mock.patch.object(module, "bench", side_effect=[baseline, candidate] * 8), \
                        contextlib.redirect_stdout(io.StringIO()):
                    self.assertEqual(module.main(), 1)


if __name__ == "__main__":
    unittest.main()
