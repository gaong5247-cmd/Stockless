#!/usr/bin/env python3
from __future__ import annotations

import math
import re
import sys

if len(sys.argv) != 3:
    raise SystemExit("usage: match_summary.py MATCH.pgn STOCKLESS_NAME")

path, target = sys.argv[1], sys.argv[2]

white = black = result = None
wins = draws = losses = 0
games = 0

tag_re = re.compile(r'^\[(\w+)\s+"(.*)"\]$')

def consume(w, b, r):
    global wins, draws, losses, games
    if not w or not b or r not in {"1-0", "0-1", "1/2-1/2"}:
        return
    if target not in (w, b):
        return
    games += 1
    if r == "1/2-1/2":
        draws += 1
    elif (r == "1-0" and w == target) or (r == "0-1" and b == target):
        wins += 1
    else:
        losses += 1

with open(path, "r", encoding="utf-8", errors="replace") as f:
    for line in f:
        line = line.strip()
        m = tag_re.match(line)
        if not m:
            continue
        key, value = m.groups()
        if key == "Event" and result is not None:
            consume(white, black, result)
            white = black = result = None
        elif key == "White":
            white = value
        elif key == "Black":
            black = value
        elif key == "Result":
            result = value

consume(white, black, result)

if games == 0:
    raise SystemExit("no target games found")

score = (wins + 0.5 * draws) / games
elo = float("inf") if score >= 1 else float("-inf") if score <= 0 else 400 * math.log10(score / (1 - score))

ex2 = (wins + 0.25 * draws) / games
var_score = max(0.0, (ex2 - score * score) / games)
se_score = math.sqrt(var_score)

if 0 < score < 1:
    derivative = 400 / math.log(10) / (score * (1 - score))
    elo_se = derivative * se_score
    lo = elo - 1.96 * elo_se
    hi = elo + 1.96 * elo_se
else:
    lo = hi = elo

print(f"games={games}")
print(f"W/D/L={wins}/{draws}/{losses}")
print(f"score={score*100:.3f}%")
print(f"elo_diff={elo:+.2f}")
print(f"elo_95ci=[{lo:+.2f}, {hi:+.2f}]")
