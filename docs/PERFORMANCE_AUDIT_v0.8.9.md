# Stockless v0.8.9 performance audit and adoption gates

Base: `Stockless_v0.8.9` (`d2e165a6ab70a9a00e1d52ba2a0f4f678ffef22f`).

## Code-path audit

- `compute_threat_signal()` constructs two complete attack maps at eligible search nodes. This is likely one of the most expensive Stockless-specific calculations. It must not be delayed or disabled without a separate strength evaluation: the previous experiment that moved the map read changed node counts.
- `make_search_policy()` is already deferred until after Stockfish's shallow pruning in the default Overdrive-OFF configuration. An earlier attempt to skip first/shallow policy calls changed the depth-12 benchmark from 1,078,618 to 773,262 nodes and was rejected. Do not revive it as a "free" speedup.
- The experimental `ThreatQuietHistory` path is OFF by default. Its additional 8,192 entries per worker and extra attack-map work cost almost nothing at runtime while disabled except storage/init. The independent holdout at weight 200 scored 47.38%; no justification to enable it by default. Deleting it is a separate breaking UCI/API decision requiring migration and test coverage.
- Search option atomics are already snapshotted once per search node. Transposition table prefetch and SIMD NNUE optimizations already exist upstream. Re-implementing them in the overlay is not justified.

## Scoped candidate

### Candidate A — side occupancy reuse (completed first CI)

The initial (side-occupancy reuse only) change was checked in GitHub Actions:
- [Build matrix](https://github.com/gaong5247-cmd/Stockless/actions/runs/39604047066): Windows, Linux, Android arm64, Android armv7 all passed.
- [Six-run deterministic bench](https://github.com/gaong5247-cmd/Stockless/actions/runs/39604047142): same 1,078,618 depth-12 nodes; median NPS 877,282 -> 877,639 (**+0.04%**, noise-sized).
- [Independent strength gates](https://github.com/gaong5247-cmd/Stockless/actions/runs/39604046794): 512 games versus frozen main: 96 W / 322 D / 94 L = 50.195%. 256 games vs official SF19: 41 W / 159 D / 56 L = 47.070%. Neither comparison establishes an Elo gain.
**Conclusion: occupancy reuse is code cleanup, not demonstrated speedup.**

### Candidate B — per-go UCI option snapshots (current unverified experiment)

Previously, each main search node executed `Stockless::search_settings()`, loading multiple relaxed atomics to get unchanged option values. The materializer now inserts a `SearchSettings` member into each Stockfish search Worker, writes it once upon entry to `Worker::start_searching()` on each UCI `go`, and reads only that local immutable snapshot in the recursive hot path. Both main and helper workers refresh it. Correctness assumption remains unchanged: UCI `setoption` happens *between* searches, not during `go`. The automated UCI smoke test now performs multiple `go` commands after changing hybrid, threats, aggression and Threads options within one engine process.

**Candidate B's first CI confirmed node-equivalent, preliminary throughput improvement:** [Actions run 39609937714](https://github.com/gaong5247-cmd/Stockless/actions/runs/39609937714) used six interleaved depth-12 tests, all searching exactly 1,078,618 nodes: baseline median 844,649 NPS, candidate median 868,819 NPS (**+2.86%**). Linux, Windows, Android arm64 and Android armv7 build checks also passed in [run 39609937800](https://github.com/gaong5247-cmd/Stockless/actions/runs/39609937800). This remains *one hosted-runner sample*, not repeatable platform-specific speed proof.

### Candidate C — eliminate remaining disabled ThreatHistory hot-path atomics

The optional ThreatHistory path defaults OFF but was still calling `threat_history_enabled()` at every MovePicker construction (reading hybrid and history atomics) and at quiet-list scoring. Cache the activation and weight at Worker go-start, pass the already-gated history pointer, and avoid redundant per-node/per-list enabled reads. Keep the exact existing history attack-map computation and scores when explicitly enabled; disable-state behavior should be unchanged. Current-head CI compiles on Linux, Windows and both Android ABIs and passes UCI smoke: [build run 39611339428](https://github.com/gaong5247-cmd/Stockless/actions/runs/39611339428). Relative to the original v0.8.9, a separate six-run depth-12 benchmark produced 914,088 -> 916,413 median NPS (**+0.25%**), with identical 1,078,618 nodes: [run 39611339394](https://github.com/gaong5247-cmd/Stockless/actions/runs/39611339394). This is not compelling evidence of a reproducible gain.

To **isolate C from B on identical hardware** rather than comparing hosted VMs, [draft PR #29](https://github.com/gaong5247-cmd/Stockless/pull/29) uses frozen B as its PR base: six interleaved AB/BA bench runs on one runner gave B 1,484,678 vs C 1,491,866 median NPS (**+0.48%; four of six pairs faster**), identical 1,078,618 nodes [run 39612226711](https://github.com/gaong5247-cmd/Stockless/actions/runs/39612226711). No repeatable significant performance win can be claimed yet.

Per-go snapshot B's exploratory independent-opening matches were mixed: versus frozen Stockless v0.8.9 it scored 73 W / 337 D / 102 L in 512 (47.168%, estimated -19.7 +/- 17.6 Elo), but versus Stockfish 19 it scored 58 W / 157 D / 41 L in 256 (53.320%, estimated +23.1 +/- 26.4 Elo). The contradictory short-time-control outcomes reinforce that **fixed-depth equivalence and preliminary NPS alone cannot justify a strength claim**. [Strength run 39609937736](https://github.com/gaong5247-cmd/Stockless/actions/runs/39609937736).

C's latest match comparisons require their own results; do not infer from B or the NPS figures.

### Independent pre-existing feature ablation (PR #25; different trees!)

On 2026-10-20, [PR #25](https://github.com/gaong5247-cmd/Stockless/pull/25) used the **same executable**, AVX2, 1 thread and four fixed-depth-12 repetitions:

| Mode | Median NPS | Depth-12 nodes | Difference vs full hybrid |
| --- | ---: | ---: | ---: |
| Hybrid ON, Threats ON, aggression 145 | 731,115 | 2,083,677 | reference |
| Hybrid ON, Threats OFF | 742,502 | 1,772,726 | +1.6% NPS |
| Hybrid ON, aggression 112 | 739,585 | 1,916,624 | +1.2% NPS |
| Hybrid OFF | 848,729 | 981,072 | +16.1% NPS |

The **search trees are different**, so neither the NPS ratio nor the lower node count is a semantics-preserving speedup. Quick 256-game color-paired matches produced NoThreats 51.172% vs FullHybrid; HybridOff 49.609% vs FullHybrid. Both are too small to establish a superiority claim. As a result, neither threats nor hybrid is removed from the default.

[Underlying ablation run](https://github.com/gaong5247-cmd/Stockless/actions/runs/39388250650).

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

### Related independent fix

[PR #26](https://github.com/gaong5247-cmd/Stockless/pull/26) already fixes mobile-Overdrive LMR cap consistency and the Windows build-script version label. This performance PR deliberately avoids copying those changes or altering mobile search decisions.

