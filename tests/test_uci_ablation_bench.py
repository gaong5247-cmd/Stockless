#!/usr/bin/env python3
"""Offline parser/option-bridge regressions for the ablation benchmark."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from uci_ablation_bench import PROFILES, command_script, parse_bench

def main():
    baseline = command_script(PROFILES["full_hybrid"], 12)
    assert "setoption name StocklessHybrid value true" in baseline
    assert "setoption name StocklessThreats value true" in baseline
    assert "setoption name StocklessOverdrive value false" in baseline
    assert "setoption name StocklessThreatHistory value false" in baseline
    assert "bench 16 1 12 default depth" in baseline
    disabled = command_script(PROFILES["no_board_threats"], 10)
    assert "setoption name StocklessThreats value false" in disabled
    pure = command_script(PROFILES["stockfish_only"], 10)
    assert "setoption name StocklessHybrid value false" in pure
    sample = "info depth 12 nodes 100 nps 500\nNodes searched: 2000000\nNodes/second: 1234567\n"
    assert parse_bench(sample) == (2000000, 1234567)
    try:
        parse_bench("no summary here")
    except ValueError:
        pass
    else:
        raise AssertionError("Missing summary should be an error")
    print("Ablation UCI option and bench parser checks passed")

if __name__ == "__main__":
    main()
