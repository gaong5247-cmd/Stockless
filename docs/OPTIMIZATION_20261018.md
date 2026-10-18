# Stockless fast-path optimization (2026-10-18)

This change is deliberately **search-semantics-preserving**. It does **not** claim an Elo
improvement, and the phrase "100% guaranteed faster" is not defensible without
measurements on the deployment CPUs.

## What changed

1. **Per-node UCI snapshot:** the four policy switches and aggression level
   are loaded from relaxed atomics once before the main move loop.
   Previously `make_search_policy()` reloaded hybrid, aggression, mobile,
   and overdrive on every considered move; overdrive was read twice.
   A `SearchSettings` struct is passed by reference to the signal and policy
   functions. UCI options should be changed between searches.
2. **Per-node correction magnitude:** `stocklessCorrectionSignal` only depends
   on the current position, so compute it before the move loop instead of
   rebuilding it for each move.
3. **Dead no-op removed:** `quietMoveAllowance` was always exactly zero.
   Removing it also removes one fragile `search.cpp` patch anchor. Unused
   `SearchInputs.staticEval`, `alpha`, and `beta` were deleted.
4. **CPU-specific PGO build path:** reuse the **pinned Stockfish** Makefile's
   `profile-build`. It compiles an instrumented engine, runs `bench`, then
   recompiles with profile data. This is an existing, documented upstream
   optimization, not a fresh untested search heuristic. On local machines,
   `ARCH=native` picks an ISA for that machine, while `x86-64-avx2` is a
   more widely compatible release target.
5. **Checks:** `tests/search_policy_test.cpp` compares 100,000 generated
   policy inputs against the previous v0.7 formula; the existing CI still
   checks Linux, Windows and Android compilation and UCI tests.
   `tools/compare_bench.py` compares stable depth benchmark nodes and
   median throughput for two actual executables.

## What was NOT transplanted from Reckless

- **Transposition-table prefetch:** already used by pinned Stockfish,
  including before regular moves (see `Search::Worker::do_move`).
- **Advanced LMR, NMP, SEE, qsearch heuristics:** both engines already tune
  these jointly with the rest of their searches. Copying constants across
  two different evaluation scales can weaken strength.
- **Reckless NNUE operation fusion or SIMD:** Stockfish has its own, heavily
  optimized NNUE inference and CPU-specific SIMD paths. The Rust code or
  Reckless weights cannot be dropped into the C++ evaluator for a guaranteed
  improvement.
- **Threat History / Selective Overdrive:** both remain OFF by default;
  Threat History weight 200 lost its 800-game independent holdout (47.38%
  score). No unconfirmed experiment was promoted to default.

## Build a tuned local engine

Linux / WSL:

```bash
STOCKLESS_ARCH=native STOCKLESS_PGO=1 STOCKLESS_JOBS=4 bash scripts/build-optimized.sh
```

Windows (MSYS2/MinGW toolchain available):

```powershell
$env:STOCKLESS_ARCH = "native"
$env:STOCKLESS_PGO = "1"
$env:STOCKLESS_JOBS = "4"
.\scripts\build-windows.ps1
```

Do not publish `ARCH=native` binaries for unknown CPUs. Keep non-PGO and
PGO binaries in separate files: rebuilding in the same materialized directory
overwrites the engine.

## Benchmark before declaring a speedup

After building two binaries from the same source version (e.g. regular vs
PGO, or before vs after this PR) using the same target architecture:

```bash
python3 tools/compare_bench.py /path/to/baseline /path/to/candidate --depth 11 --rounds 5
```

Depth-limited `bench` totals should match exactly for a semantics-preserving
optimization; the tool reports the median NPS and refuses mismatching node
counts by default. A higher NPS does not always translate into higher Elo;
confirm independent openings, two-color games, STC **and** LTC if considering
default search-policy changes.

### Adoption gates

- Compile with the pinned Stockfish and Reckless SHAs (materializer checks).
- Verify Linux, Windows, Android, UCI and policy invariants.
- Same-depth signatures / counts must match for intended no-op refactors.
- Positive median NPS after repeated interleaved runs.
- Any heuristic or pruning change requires statistical match evidence before
  shipping as the default, regardless of whether it originated in Reckless.

## First completed same-runner speed measurements

[GitHub Actions run #39086996198](https://github.com/gaong5247-cmd/Stockless/actions/runs/39086996198),
2026-10-18. Ubuntu runner, `ARCH=x86-64-avx2`, one search thread,
16 MiB hash, fixed-depth 10, four interleaved repeats per executable.
All measured depth-limited runs searched **282,984 nodes**.

| Comparison | First median NPS | Second median NPS | Change |
| --- | ---: | ---: | ---: |
| Frozen v0.7 → search-snapshot source | 769,000 | 774,250 | **+0.68%** |
| Same source: non-PGO → PGO | 771,280 | 821,449 | **+6.50%** |

This is **preliminary NPS evidence only**. A 0.68% difference is well within
plausible runner jitter, and four short depth-10 runs are insufficient to
claim a reliable improvement of that size. The PGO outcome is encouraging,
but verify locally on target CPUs using `--depth 13 --rounds 20`, and use
paired matches to evaluate any playing-strength change. The two comparisons
are separate AB/BA sequences; do not combine their median NPS values to
report a direct end-to-end speedup.

## Further investigation (separate candidate PRs)

A small *bounded* per-position threat cache, more precise move-order
use of existing Stockfish attack maps, and CPU-dependent local PGO/ISA builds
might be useful. They are **not included** without a benchmark and
non-regression proof; changing depth reductions without games is not safe.
