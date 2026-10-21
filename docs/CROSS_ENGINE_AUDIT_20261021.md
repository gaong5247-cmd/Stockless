# Stockless v0.8.9 — cross-engine search/NNUE audit (2026-10-21)

**Objective:** Reuse *verified ideas* only when the same capability is not already present in the pinned Stockfish core, and delete unproven custom layers instead of accumulating speculative heuristics. This document records code-level comparisons, **not** external engines' Elo as proof of a Stockless speedup.

## Repositories reviewed

| Engine (source) | Technique examined | Present in pinned Stockfish? | Decision for Stockless |
| --- | --- | --- | --- |
| [Stockfish](https://github.com/official-stockfish/Stockfish/tree/0a215d6c9e48856ef630013b8ab8312941a59057) | Recursive PVS/LMR, TT prefetch before make-move, shared continuation/correction history, SIMD/incremental NNUE | **Yes**; core itself | Keep/tune upstream; do **not** re-implement |
| [Berserk](https://github.com/jhonnold/berserk/blob/main/src/search.c) | TT prefetch, history-conditioned LMR, SEE pruning, history move ordering | Search and prefetch already exist in Stockfish | No direct transplant; coefficients and NNUE scale differ |
| [Ethereal](https://github.com/AndyGrant/Ethereal/blob/master/src/search.c) | Staged move picker, ProbCut, SEE, futility and continuation-history pruning | Overlap with native Stockfish | No raw parameter copy; benchmark separate bounded experiments |
| [RubiChess](https://github.com/Matthies/RubiChess/blob/master/src/search.cpp) | Early next TT entry prefetch, history-aware LMR | Core already prefetches before `pos.do_move` | Reject duplicate TT prefetch |
| [Stormphrax](https://github.com/Ciekce/Stormphrax/blob/main/src/search.cpp) | Reuses position threat classifications across History, reductions and move ordering | Stockfish's NNUE full-threat features are **not** equivalent to a reusable board attack map | Possible future **position-state-level** threat cache, but cache invalidation and change to Position are costly; profile first |
| [PlentyChess](https://github.com/Yoshie2000/PlentyChess) | Threat-input NNUE and trained evaluation; portable PGO builds | Different trained weights/feature transformer; native Stockfish already has PGO Makefile path | Do **not** splice incompatible weights or duplicate compiler flags |
| [Caissa](https://github.com/Witek902/Caissa/blob/master/src/backend/Search.cpp) | Node cache, TT prefetch, instrumentation to explain search | TT/NNUE optimization exists; node cache is an additional, nontrivial policy | Keep as independent large experiment only |
| [Viridithas](https://github.com/cosmobobak/viridithas) | Threat-classified history and Rust search organization | Similar concepts, different representation/language | Design reference only; no wholesale Rust/C++ rewrite |

All engine implementations are independently developed and heavily coupled to their own evaluation scales, legal move encodings, table layouts and hash keys. **No third-party source code was copied into Stockless by this experiment.** Preserve AGPL/GPL/MIT upstream credits and pinned SHA provenance.

### Concrete duplicates identified

1. [Pinned Stockfish search](https://github.com/official-stockfish/Stockfish/blob/0a215d6c9e48856ef630013b8ab8312941a59057/src/search.cpp) already executes `prefetch(tt.first_entry(pos.prefetch_key(move)))` in `Search::Worker::do_move`, along with correction-history prefetch. Berserk, RubiChess, Stormphrax and Caissa also prefetch child TT entries. Adding a second prefetch to Stockless's search overlay only adds complexity.
2. Native Stockfish provides SEE move filtering, LMR, NMP, ProbCut, TT/correction/continuation histories and incremental NNUE. Do not transplant numeric thresholds without matched strength tests.
3. Separate *Reckless-inspired ThreatQuietHistory* in the Stockless overlay consumes **8,192 entries × 10 bytes = 81,920 bytes per Worker** (plus alignment and class bookkeeping; layout must be verified by compile). It also changes `search.h`, `movepick.h`, `movepick.cpp`, `search.cpp`, and UCI setup through dozens of text patch anchors. This experiment's primary deletion removes those integration points.

### Why ThreatHistory is a legitimate removal candidate

[Independent v0.7 report](https://github.com/gaong5247-cmd/Stockless/blob/Stockless_v0.8.9/docs/HISTORY_TUNING_REPORT.md):
- A screening sample favored weight 200, but the independent **800-game** confirmation scored **226 W / 306 D / 268 L = 47.375%**, not a verified improvement.
- A separate 600-game comparison vs pinned Stockfish scored 48.92% with ThreatHistory OFF vs 48.08% for ON weight 200.
- The stable default has always been OFF. Removing the subsystem is a legitimate **memory, source and hot-path overhead reduction experiment**, not proof of strength improvement.

### Scope and compatibility

- Remove the experimental history table, score updates, MovePicker integration, UCI atomics/options and history-specific tournament scripts/tests/workflows from **this experimental lean branch only**.
- Keep `StocklessHybrid`, `StocklessAggression`, `StocklessThreats`, `StocklessOverdrive`, `StocklessMobile` with unchanged values/defaults.
- Retire the UCI options `StocklessThreatHistory` and `StocklessHistoryWeight` **only in this candidate**. This is explicitly a **breaking UCI interface change**: GUIs or scripts that set those options must be updated. Published v0.8.9 releases and `main` remain unchanged.
- Continue to preserve prior experiment results under the immutable `Stockless_v0.8.9` Git tag; link historical docs to their frozen source tag.
- Do not delete or bypass the primary threat-signal generator in this patch; whether `StocklessThreats` helps at fixed time is a separate question tested in [PR #25](https://github.com/gaong5247-cmd/Stockless/pull/25).
- No direct foreign engine transplant; licensing and algorithmic attribution are preserved.

## Verification and promotion gates

1. `python3 tools/materialize.py` against the **same pinned Stockfish/Reckless** revisions and build for Linux/Windows/Android.
2. `tests/search_policy_test.cpp` must reproduce all frozen v0.7 policy outputs and `tests/uci_lean_smoke.py` must check option changes, helper threads and real bestmove.
3. Compare **exact depth-12 node totals** against v0.8.9 (6× AB/BA, same ISA, flags, NNUE, threads); failing same-node decisions rejects the speed-only claim.
4. Measure repeated NPS on fixed hardware, high depth, warmup and different CPUs/ISAs. Small hosted-CI changes are noise until repeated.
5. Matches against unmodified v0.8.9, with independent books, color pairs, STC and LTC where practical, to catch **unexpected** strength regressions. No Elo claim from NPS.
6. If memory and NPS benefits are immaterial or UCI compatibility cost is too high, **do not merge** this removal.
7. In separate candidate PRs consider:
   - Caissa-/Stormphrax-style threat caching only with *correct make/unmake invalidation*;
   - Stockfish upstream NNUE refresh/prefetch changes only after profiling and network compatibility checks;
   - selective threat-scan gating only with strength experiments (not a semantics-preserving optimization).

**State: experimental audit, not an approved release.**
