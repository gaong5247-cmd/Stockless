# Stockless hybrid / threat ablation (2026-10-20)

**A/B research, not a default change.**

Question: Stockfish SFNNv18 already has neural threat features and
incremental threat updates. Does Stockless's separate board attack-map
computation contribute enough **playing strength** to justify its CPU cost?

Same binary, same CPU target, same official color-swapped opening book:

1. FullHybrid: Hybrid ON, Threats ON, Aggression 145 (reference).
2. NoThreats: Hybrid ON, Threats OFF, Aggression 145.
3. HybridOff: Hybrid OFF, using underlying Stockfish search/NNUE.
4. Aggression112: an additional fixed-depth performance sample only.

See `tools/uci_ablation_bench.py` for interleaved descriptive NPS and
`.github/workflows/hybrid-threat-ablation.yml` for two 256-game paired
color-swap quick comparisons. NPS changes across different search trees
are not Elo gains. The W/D/L confidence interval printed by the current
summary is a preliminary game-level approximation, not a paired SPRT.

**Remove or rewrite `threat_signal.h` only if repeated STC and LTC A/B
games actually favor NoThreats or HybridOff.**
If removing the feature raises speed but hurts Elo, explore a gated /
lower-frequency threat signal separately. Preserve user-facing UCI
compatibility and avoid large untested search-policy changes.
