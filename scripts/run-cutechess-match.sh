#!/usr/bin/env bash
set -euo pipefail

if [ "$#" -lt 4 ]; then
  echo "usage: $0 OPPONENT_CMD OPPONENT_NAME OUT_PGN GAMES [TC] [CONCURRENCY]" >&2
  exit 2
fi

OPPONENT_CMD=$1
OPPONENT_NAME=$2
OUT_PGN=$3
GAMES=$4
TC=${5:-0.2+0.002}
CONCURRENCY=${6:-2}
# Keep arena defaults aligned with the engine's actual UCI defaults.
# Historical sweeps must pass explicit STOCKLESS_* environment overrides.
AGGRESSION=${STOCKLESS_AGGRESSION:-145}
OVERDRIVE=${STOCKLESS_OVERDRIVE:-false}
THREATS=${STOCKLESS_THREATS:-true}
MOBILE=${STOCKLESS_MOBILE:-false}
# The pinned Reckless UCI spelling differs from Stockfish/Stockless. Allow
# custom engine labels to supply their advertised option name explicitly.
case "$OPPONENT_NAME" in
  Reckless*) DEFAULT_OPPONENT_OVERHEAD_OPTION=MoveOverhead ;;
  *) DEFAULT_OPPONENT_OVERHEAD_OPTION="Move Overhead" ;;
esac
OPPONENT_OVERHEAD_OPTION="${OPPONENT_MOVE_OVERHEAD_OPTION:-$DEFAULT_OPPONENT_OVERHEAD_OPTION}"

ROOT=$(cd "$(dirname "$0")/.." && pwd)
CUTECHESS=${CUTECHESS:-cutechess-cli}
STOCKLESS=${STOCKLESS:-"$ROOT/build/stockless-src/src/stockless"}
OPENINGS=${OPENINGS:-"$ROOT/tests/openings.epd"}
OPENING_FORMAT=${STOCKLESS_OPENING_FORMAT:-epd}

if (( GAMES % 2 != 0 )); then
  echo "GAMES must be even so -repeat can swap colors fairly" >&2
  exit 2
fi

mkdir -p "$(dirname "$OUT_PGN")"

"$CUTECHESS" \
  -tournament round-robin \
  -engine name=Stockless cmd="$STOCKLESS" \
    option.Threads=1 option.Hash=32 "option.Move Overhead=1" \
    option.StocklessHybrid=true option.StocklessAggression="$AGGRESSION" \
    option.StocklessThreats="$THREATS" option.StocklessOverdrive="$OVERDRIVE" option.StocklessMobile="$MOBILE" \
  -engine name="$OPPONENT_NAME" cmd="$OPPONENT_CMD" \
    option.Threads=1 option.Hash=32 "option.${OPPONENT_OVERHEAD_OPTION}=1" \
  -each proto=uci tc="$TC" \
  -games "$GAMES" \
  -repeat \
  -concurrency "$CONCURRENCY" \
  -openings file="$OPENINGS" format="$OPENING_FORMAT" order=random \
  -draw movenumber=40 movecount=8 score=10 \
  -resign movecount=4 score=700 \
  -recover \
  -pgnout "$OUT_PGN"
