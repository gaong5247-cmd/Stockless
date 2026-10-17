#!/usr/bin/env bash
# Compare the same Stockless binary with ThreatHistory ON vs OFF.
# Requires cutechess-cli, a materialized/built Stockless binary, and openings.epd.
set -euo pipefail

ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
STOCKLESS=${STOCKLESS:-"$ROOT/build/stockless-src/src/stockless"}
CUTECHESS=${CUTECHESS:-cutechess-cli}
OPENINGS=${OPENINGS:-"$ROOT/tests/openings.epd"}
GAMES=${1:-600}
TC=${2:-0.2+0.002}
CONCURRENCY=${3:-2}
WEIGHT=${STOCKLESS_HISTORY_WEIGHT:-100}
OUT_PGN=${OUT_PGN:-"$ROOT/results/history-on-vs-off.pgn"}

if (( GAMES <= 0 || GAMES % 2 != 0 )); then
  echo "GAMES must be a positive, even integer for color-swapped pairs" >&2
  exit 2
fi
[[ -x "$STOCKLESS" ]] || { echo "Build Stockless first: $STOCKLESS" >&2; exit 2; }
[[ -f "$OPENINGS" ]] || {
  echo "Missing $OPENINGS; run: pip install python-chess && python tools/make_openings.py tests/opening_lines.txt tests/openings.epd" >&2
  exit 2
}
mkdir -p "$(dirname "$OUT_PGN")"

"$CUTECHESS" \
  -tournament round-robin \
  -engine name=HistoryON cmd="$STOCKLESS" \
    option.Threads=1 option.Hash=32 option.MoveOverhead=1 \
    option.StocklessHybrid=true option.StocklessThreatHistory=true \
    option.StocklessHistoryWeight="$WEIGHT" option.StocklessOverdrive=false \
  -engine name=HistoryOFF cmd="$STOCKLESS" \
    option.Threads=1 option.Hash=32 option.MoveOverhead=1 \
    option.StocklessHybrid=true option.StocklessThreatHistory=false \
    option.StocklessHistoryWeight="$WEIGHT" option.StocklessOverdrive=false \
  -each proto=uci tc="$TC" \
  -games "$GAMES" -repeat -concurrency "$CONCURRENCY" \
  -openings file="$OPENINGS" format=epd order=random \
  -draw movenumber=40 movecount=8 score=10 \
  -resign movecount=4 score=700 \
  -recover -pgnout "$OUT_PGN"

python "$ROOT/tools/match_summary.py" "$OUT_PGN" HistoryON
