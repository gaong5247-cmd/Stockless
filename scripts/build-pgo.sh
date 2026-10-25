#!/usr/bin/env bash
# Auditable GCC/MinGW PGO for a native, fixed-ISA executable.
# Every profile-use object is rebuilt, and instrumented output is rejected.
set -euo pipefail

pgo_src="${1:?Usage: build-pgo.sh SOURCE_DIR [ARCH] [gcc|mingw] [JOBS]}"
pgo_arch="${2:-x86-64-avx2}"
pgo_comp="${3:-gcc}"
pgo_jobs="${4:-4}"
case "$pgo_comp" in gcc|mingw) ;; *) echo 'This helper requires GCC or MinGW GCC' >&2; exit 2 ;; esac
case "$pgo_arch" in *universal*|*wasm*) echo 'PGO helper requires one natively executable ISA' >&2; exit 2 ;; esac
[[ "$pgo_jobs" =~ ^[1-9][0-9]*$ ]] || { echo 'JOBS must be positive' >&2; exit 2; }
pgo_src="$(cd "$pgo_src" && pwd)"
pgo_binary="$pgo_src/stockless"
if [[ "$pgo_comp" == mingw || "${OS:-}" == Windows_NT ]]; then
    pgo_binary="$pgo_binary.exe"
fi

make -C "$pgo_src" "ARCH=$pgo_arch" "COMP=$pgo_comp" net
make -C "$pgo_src" "ARCH=$pgo_arch" "COMP=$pgo_comp" objclean
make -C "$pgo_src" "ARCH=$pgo_arch" "COMP=$pgo_comp" profileclean
make -C "$pgo_src" "-j$pgo_jobs" "ARCH=$pgo_arch" "COMP=$pgo_comp" gcc-profile-make
test -x "$pgo_binary"
(
    cd "$pgo_src"
    "$pgo_binary" bench > pgo-training.log 2>&1
)
tail -n 4 "$pgo_src/pgo-training.log"
test -n "$(find "$pgo_src/profdir" -name '*.gcda' -print -quit)"

make -C "$pgo_src" "ARCH=$pgo_arch" "COMP=$pgo_comp" objclean
if [[ -n "$(find "$pgo_src" -maxdepth 1 -type f -name '*.o' -print -quit)" ]]; then
    echo 'PGO cleanup left object files; refusing mixed instrumentation' >&2
    exit 1
fi
# -B forces all translation units through profile-use even if a stale object is
# found through VPATH or has an unexpected timestamp. Profile data is retained.
make -B -C "$pgo_src" "-j$pgo_jobs" "ARCH=$pgo_arch" "COMP=$pgo_comp" gcc-profile-use
nm --defined-only "$pgo_binary" > "$pgo_src/pgo-symbols.txt"
if grep -Eq '(__gcov0|__gcov_merge|__gcov_init|__llvm_profile)' "$pgo_src/pgo-symbols.txt"; then
    echo 'Final PGO binary still contains instrumentation; refusing to ship or test it' >&2
    exit 1
fi
make -C "$pgo_src" "ARCH=$pgo_arch" "COMP=$pgo_comp" profileclean
echo "Verified clean PGO executable: $pgo_binary"
