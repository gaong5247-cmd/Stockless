#!/usr/bin/env bash
# Local high-performance Stockless build: native ISA + pinned Stockfish PGO.
# This is CPU-specific; do not distribute ARCH=native builds as universal binaries.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

ARCH="${STOCKLESS_ARCH:-native}"
JOBS="${STOCKLESS_JOBS:-2}"
PGO="${STOCKLESS_PGO:-1}"

if ! [[ "$JOBS" =~ ^[0-9]+$ ]] || [ "$JOBS" -lt 1 ]; then
    echo "STOCKLESS_JOBS must be a positive integer" >&2
    exit 2
fi

case "$PGO" in
    0) TARGET=build ;;
    1) TARGET=profile-build ;;
    *) echo "STOCKLESS_PGO must be 0 or 1" >&2; exit 2 ;;
esac

git submodule update --init --recursive
python3 tools/materialize.py
echo "[Stockless] make $TARGET ARCH=$ARCH JOBS=$JOBS"
if [ "$PGO" = 1 ]; then
    bash scripts/build-pgo.sh build/stockless-src/src "$ARCH" gcc "$JOBS"
else
    make -C build/stockless-src/src "-j$JOBS" "$TARGET" "ARCH=$ARCH"
fi
echo "[Stockless] binary: build/stockless-src/src/stockless"
echo "[Stockless] ARCH=native is host-specific. Use STOCKLESS_ARCH=x86-64-avx2 for portable AVX2."
