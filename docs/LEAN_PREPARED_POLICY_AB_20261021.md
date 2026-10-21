# Combined candidate: lean history removal + prepared search policy

**Base:** experimental [lean PR #33](https://github.com/gaong5247-cmd/Stockless/pull/33), not stable `main`. This PR adds only the per-node arithmetic refactor from [PR #30](https://github.com/gaong5247-cmd/Stockless/pull/30).

## Why this combination

- Lean history removal has two same-node AVX2 preliminary comparisons: **+1.82%** and **+1.92%** median NPS against frozen v0.8.9 (separate hosted runners). This does **not** establish Elo improvement and deletes two deprecated UCI options.
- The previously tested node-invariant preparation in [PR #30, run #39616904614](https://github.com/gaong5247-cmd/Stockless/actions/runs/39616904614) gave **+1.69%** NPS on a different runner and passed exact nodes and bestmoves across nine UCI profiles. Its early bug caching `ss->ttPv` was corrected; `ss->ttPv`, `beta-alpha`, child cutoff counts and capture/check flags remain live.
- A proposed per-go Worker settings cache [PR #34](https://github.com/gaong5247-cmd/Stockless/pull/34) was instead **rejected**: direct against lean it scored **−0.25%** NPS; adding complexity without benefit is unwarranted.
- This experiment combines the two more promising independent changes, **not** a grab-bag of NNUE weights, hash formats and tuned constants from unrelated engines.

## Scope and risk

`prepare_search_policy()` computes per-node pressure/danger/volatility bases, search cap and stable flags; `make_prepared_move_policy()` handles current move-specific features. Original `make_search_policy()` is a single shared wrapper, eliminating duplicate formulas. Native Stockfish NNUE, NMP, ProbCut, TT prefetch and UCI search defaults are untouched. No third-party code is copied.

The lean branch already intentionally retires `StocklessThreatHistory` and `StocklessHistoryWeight`; do not assume the public release interface matches this research version.

## Validation gates

1. `optimization-benchmark` builds frozen *lean* and combined using the same AVX2 compiler, flags, NNUE. **All depth-12 bench node counts must match exactly**.
2. An added `tools/compare_lean_policy_profiles.py` step checks identical nodes **and bestmove sequences** at depth 9 for **eight retained UCI profiles**: default, hybrid OFF, threats OFF, aggression 0/200, Overdrive on desktop/mobile, and mobile profile.
3. Linux, Windows, Android arm64 and armv7 builds and `tests/uci_lean_smoke.py` pass.
4. Require repeated A/B NPS on fixed hardware at multiple depths. If the combined benefit is negligible, revert this layer.
5. Paired color-swapped STC/LTC matches versus lean and original v0.8.9 to check that strength has not regressed. A fixed-depth node match and NPS gain do **not** prove higher Elo.

No auto-merge, no release and no upgraded Elo claim.
