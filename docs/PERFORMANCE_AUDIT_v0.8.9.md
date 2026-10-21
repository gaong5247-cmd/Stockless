# Stockless v0.8.9 performance audit and adoption gates

Base: `Stockless_v0.8.9` (`d2e165a6ab70a9a00e1d52ba2a0f4f678ffef22f`).

## Code-path audit

- `compute_threat_signal()` constructs two complete attack maps at eligible search nodes. This is likely one of the most expensive Stockless-specific calculations. It must not be delayed or disabled without a separate strength evaluation: the previous experiment that moved the map read changed node counts.
- `make_search_policy()` is already deferred until after Stockfish's shallow pruning in the default Overdrive-OFF configuration. An earlier attempt to skip first/shallow policy calls changed the depth-12 benchmark from 1,078,618 to 773,262 nodes and was rejected. Do not revive it as a "free" speedup.
- The experimental `ThreatQuietHistory` path is OFF by default. Its additional 8,192 entries per worker and extra attack-map work cost almost nothing at runtime while disabled except storage/init. The independent holdout at weight 200 scored 47.38%; no justification to enable it by default. Deleting it is a separate breaking UCI/API decision requiring migration and test coverage.
- Search option atomics are already snapshotted once per search node. Transposition table prefetch and SIMD NNUE optimizations already exist upstream. Re-implementing them in the overlay is not justified.

## Scoped candidate

Reuse already-selected side occupancy bitboards in `compute_threat_signal()` rather than repeating `Position::pieces(color)` lookups. No changes to feature definitions, arithmetic order, output bounds, activation gates, search heuristics, NNUE files, UCI defaults, or platform dispatch. This is a tiny candidate and compilers may already eliminate the redundant loads: **NPS improvement is not yet demonstrated**.

## Validation (mandatory before merge)

1. `python3 tools/materialize.py` after `git submodule update --init --recursive`, verifying the pinned Stockfish/Reckless SHAs.
2. Build baseline and candidate using the same `ARCH=x86-64-avx2`, compiler and flags, without reusing the same build directory.
3. `python3 tools/compare_bench.py /path/to/baseline /path/to/candidate --depth 13 --rounds 20`. Require identical node counts in every round. Record medians and variability; repeat locally on CPU hardware with AB/BA interleaving.
4. Run Linux/Windows/Android build CI and UCI smoke tests, plus the search-policy reference tests.
5. Even for a semantics-preserving patch, test supported runtime platforms. For future policy/attack-timing changes, run opening-paired color-swapped matches (STC and LTC, sequential SPRT/pentanomial evaluation).

**Merge decision:** only if controlled repeated benchmarks establish a meaningful reproducible gain or the refactor has compelling maintenance benefit without regression. Do not claim a speedup or Elo increase from this PR alone.

## High-priority follow-up experiments (separate PRs)

1. Benchmark `StocklessThreats=false` versus true at fixed time and with paired matches to quantify threat-map cost versus strength impact; disabling it changes playing policy and cannot be silently adopted.
2. A/B PGO release-target builds on each CPU architecture; earlier hosted experiment indicated a preliminary +6.50% NPS but has not been confirmed on target CPUs.
3. Compare threat-map profiling samples / CPU call stacks before implementing caches. Avoid caching mutable `Position` pointers or stale per-position attack maps across make/unmake.

No experimental history module or user-facing option has been deleted here; unsupported dead-code deletion would risk breaking existing workflows.
