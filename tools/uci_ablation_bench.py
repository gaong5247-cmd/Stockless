#!/usr/bin/env python3
"""Profile existing Stockless UCI feature toggles WITHOUT modifying engine code.

Fixed-depth trees may differ between configurations. Throughput is NOT
evidence of Elo; only color-paired games can test playing strength.
"""
from __future__ import annotations

import argparse
import json
import re
import statistics
import subprocess
from pathlib import Path

NODE_RE = re.compile(r"Nodes searched\s*:\s*([0-9]+)")
NPS_RE = re.compile(r"Nodes/second\s*:\s*([0-9]+)")

PROFILES = {
    "full_hybrid": {"StocklessHybrid": "true", "StocklessThreats": "true", "StocklessAggression": "145"},
    "no_board_threats": {"StocklessHybrid": "true", "StocklessThreats": "false", "StocklessAggression": "145"},
    "aggression_112": {"StocklessHybrid": "true", "StocklessThreats": "true", "StocklessAggression": "112"},
    "stockfish_only": {"StocklessHybrid": "false", "StocklessThreats": "false", "StocklessAggression": "145"},
}

def command_script(profile: dict[str, str], depth: int) -> str:
    options = {
        "StocklessHybrid": "true",
        "StocklessAggression": "145",
        "StocklessThreats": "true",
        "StocklessMobile": "false",
        "StocklessOverdrive": "false",
        "StocklessThreatHistory": "false",
        **profile,
    }
    lines = [f"setoption name {name} value {value}" for name, value in options.items()]
    return "\n".join([*lines, "isready", f"bench 16 1 {depth} default depth", "quit", ""])

def parse_bench(text: str) -> tuple[int, int]:
    nodes, nps = NODE_RE.findall(text), NPS_RE.findall(text)
    if not nodes or not nps:
        raise ValueError(f"Missing native Stockfish bench summary: {text[-1500:]}")
    count, speed = int(nodes[-1]), int(nps[-1])
    if count <= 0 or speed <= 0:
        raise ValueError("Bench node count and NPS must be positive")
    return count, speed

def run(binary: Path, name: str, depth: int, timeout: int) -> tuple[int, int]:
    output = subprocess.run(
        [str(binary)], cwd=binary.parent,
        input=command_script(PROFILES[name], depth),
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        text=True, encoding="utf-8", errors="replace",
        timeout=timeout, check=True,
    )
    return parse_bench(output.stdout)

def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("binary", type=Path)
    p.add_argument("--depth", type=int, default=12)
    p.add_argument("--rounds", type=int, default=4)
    p.add_argument("--timeout", type=int, default=360)
    p.add_argument("--json-output", type=Path)
    args = p.parse_args()
    if args.depth < 1 or args.rounds < 1 or args.timeout < 1:
        p.error("depth, rounds and timeout must be positive")
    binary = args.binary.resolve(strict=True)
    names = list(PROFILES)
    samples: dict[str, list[tuple[int,int]]] = {name: [] for name in names}
    for rep in range(args.rounds):
        order = names if rep % 2 == 0 else list(reversed(names))
        for name in order:
            nodes, nps = run(binary, name, args.depth, args.timeout)
            samples[name].append((nodes, nps))
            print(f"round={rep+1} {name}: nodes={nodes:,} nps={nps:,}", flush=True)

    baseline_nps = statistics.median(x[1] for x in samples["full_hybrid"])
    summary = {}
    for name in names:
        values = samples[name]
        count_set = sorted(set(n for n, _ in values))
        median_nps = statistics.median(nps for _, nps in values)
        ratio = median_nps / baseline_nps
        summary[name] = {"nodes_observed": count_set, "median_nps": median_nps,
                         "relative_to_full_hybrid": ratio}
        print(f"{name}: nodes={count_set} median_nps={median_nps:,.0f} ratio={ratio:.3f}")
    print("NOTE: configs may search different trees; these NPS ratios are NOT Elo or identical-work speedups.")
    print("Use color-swapped paired games and independent STC/LTC to decide whether to remove a feature.")
    if args.json_output:
        args.json_output.parent.mkdir(parents=True, exist_ok=True)
        args.json_output.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")

if __name__ == "__main__":
    main()
