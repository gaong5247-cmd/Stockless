# Lean Stockless + per-Worker search option snapshot (2026-10-21)

**Research comparison:** base is [lean removal PR #33](https://github.com/gaong5247-cmd/Stockless/pull/33), not the public stable release. This candidate is a second independent optimization layered on that lean baseline; do not confuse its NPS result with the total v0.8.9 speed change.

## Cross-engine rationale

Several engines (notably [Caissa](https://github.com/Witek902/Caissa/blob/master/src/backend/Search.cpp) and [Stormphrax](https://github.com/Ciekce/Stormphrax/blob/main/src/search.cpp)) keep per-worker/per-node search state instead of reconstructing unchanged data for every move. The pinned Stockfish search Worker owns its own mutable histories and caches. Stockless's optional hybrid policy settings were still loaded from relaxed global atomics at every recursive node.

This experiment follows that general ownership principle, **without copying code**, and stores `SearchSettings` inside each Stockfish Worker:

- `start_searching()` captures the UCI settings once at the beginning of every `go` for main and helper Workers.
- The hot search loop takes a const reference to that snapshot instead of multiple relaxed atomic reads.
- UCI `setoption` is required between searches, not while one is running. `tests/uci_lean_smoke.py` changes settings and thread count across searches in one engine process.
- `tests/search_policy_test.cpp` verifies snapshot immutability across simulated settings changes.
- The independent v0.8.9 strength policy and the lean removal stay unchanged: same NNUE, same attack maps, same LMR/pruning, same UCI defaults and the same two retired legacy history options as base #33.

## Adoption requirements

1. Compile for Linux, Windows and Android (arm64 and armv7); exercise search with `Threads` 1 and 2.
2. Compare **directly with lean PR #33 base**, same compiler, CPU ISA and NNUE; depth-limited nodes must match exactly.
3. Six AB/BA rounds are exploratory. Repeat on different machines and depths; distinguish runtime throughput from NNUE speed and Elo.
4. 512 paired-color baseline games against the lean version, plus STC/LTC before a strength claim.
5. Promote only if this combined version reliably beats lean in *throughput* with non-regression, and does not introduce any dynamic UCI changes mid-search.

**No merge or release unless validation supports it.**
