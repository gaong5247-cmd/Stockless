# Stockless v0.8.2: experimental modern NNUE PGO, no stable changes

This experiment changes **only the compiler optimization process**, not Stockless search/NNUE source, the original pinned submodules or official releases.

## Background

The independent Stockless v0.8.1 modern SFNNv18 confirmation scored 265 wins, 302 draws, 233 losses (52.00%) against frozen v0.7 over 800 games, an estimated +13.90 relative Elo. The approximate 95% Elo interval included 0, so this is promising but inconclusive and misses the >55% performance goal.

Previous project experiments observed a preliminary +6.50% NPS from Stockfish's profile-guided build using the old September upstream. That speed effect must be remeasured with the October modern K32Q2/SFNNv18 NNUE rather than assumed.

## Controlled experiment

1. Build frozen v0.7 from its exact release tag, separately.
2. Temporarily check out official Stockfish effdc3fd3f6de6e75fe1374a51a7a7eed66f880b in the GitHub runner, leaving the committed September Stockfish gitlink unchanged.
3. Materialize modern Stockless with STOCKLESS_UPSTREAM_TRACK=modern-v18 and build one stockless-standard using ARCH=x86-64-avx2.
4. Invoke the official Stockfish Makefile profile-build target **on the exact same source and ISA** and copy stockless-pgo to a separate binary filename.
5. Verify both binaries report identical UCI options and their fixed-depth benchmark nodes match exactly; then interleave six separate speed runs to compare median NPS. Depth-11 node mismatches fail before any matches.
6. Play 200 two-color, official-EPD games between stockless-pgo and stockless-standard, with matching UCI settings. No search heuristic, NNUE architecture or opening book changes are permitted.
7. Play 200 PGO modern versus frozen v0.7 exploratory games, and another **independent 800-game holdout** with a disjoint official Stockfish opening set.
8. Retain detailed PGN/logs and reject unfinished/malformed results, and do not promote defaults or overwrite stable artifacts.

Short smoke mode uses fewer games and **cannot** establish strength gains.

### Full experiment acceptance

The end goal is strictly above 55% against frozen Stockless v0.7, on the 800-game independent holdout. A fixed-sample 95% lower confidence bound above 50% is a preliminary guard, not a substitute for formal SPRT or LTC validation.

Positive NPS alone does **not** imply positive Elo. An isolated 200-game PGO vs standard result is exploratory; a stronger claim requires independent larger matches. Selection is fixed before testing; there is no tuning on the holdout.

CI workflow: .github/workflows/v082-modern-pgo.yml.
Local results will appear under results/v082-pgo-on-off and results/v082-pgo-v07 in the workflow artifact.

This branch is review-only and must not be treated as a new stable release before these tests pass.
