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

ROOT=$(cd "$(dirname "$0")/.." && pwd)
CUTECHESS=${CUTECHESS:-cutechess-cli}
STOCKLESS=${STOCKLESS:-"$ROOT/build/stockless-src/src/stockless"}
OPENINGS=${OPENINGS:-"$ROOT/tests/openings.epd"}

if (( GAMES % 2 != 0 )); then
  echo "GAMES must be even so -repeat can swap colors fairly" >&2
  exit 2
fi

mkdir -p "$(dirname "$OUT_PGN")"

"$CUTECHESS" \
  -tournament round-robin \
  -engine name=Stockless cmd="$STOCKLESS" \
    option.Threads=1 option.Hash=32 option.MoveOverhead=1 \
    option.StocklessHybrid=true option.StocklessAggression=112 \
    option.StocklessThreats=true option.StocklessOverdrive=true option.StocklessMobile=false \
  -engine name="$OPPONENT_NAME" cmd="$OPPONENT_CMD" \
    option.Threads=1 option.Hash=32 option.MoveOverhead=1 \
  -each proto=uci tc="$TC" \
  -games "$GAMES" \
  -repeat \
  -concurrency "$CONCURRENCY" \
  -openings file="$OPENINGS" format=epd order=random \
  -draw movenumber=40 movecount=8 score=10 \
  -resign movecount=4 score=700 \
  -recover \
  -pgnout "$OUT_PGN"
