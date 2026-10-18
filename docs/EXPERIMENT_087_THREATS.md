# Stockless v0.8.7 — prospective Threats OFF confirmation

**Experimental setting only. Original Stockfish and Reckless submodules, Stockless code, UCI defaults and stable releases are unchanged.**

The modern Stockless v0.8.2 engine (upstream Stockfish SFNNv18/K32Q2 `effdc3fd3f6de6e75fe1374a51a7a7eed66f880b`, GCC PGO, Stockless hybrid aggression 145) previously scored **54.6875% vs frozen v0.7 in 800 games**. Subsequent v0.8.3 UCI screening (200 games each) showed `StocklessThreats=false` scored **54.50%** versus **53.25%** for the default. This is an exploratory result, not proof that disabling threats improves playing strength.

## Predeclared validation

This branch fixes a single candidate, `ThreatsOff145`, before the new holdout. We use the existing source/compilers, exact modern Stockfish SHA, same PGO training target, x86-64 AVX2, Threads 1, Hash 32, MoveOverhead 1, Overdrive OFF, ThreatHistory OFF, SearchProfile=0, Aggression=145.

- Candidate: `StocklessThreats=false` (no additional code changes)
- Frozen opponent: Stockless_v0.7 at `261d46be460cb8c83b2d883e8366bcc9d3f09b27`
- Screening: 200 color-swapped EPD games, 0.2+0.002
- **Fresh independent holdout: 800 games**, 0.4+0.004, separate EPD subset
- Seed: 20261029, different from the previous v0.8.3 experiment's 20261022 split. Since both derive from one official EPD archive, the samples may overlap at some positions; do not claim a universally independent book.
- **Strict gate**: observed holdout score >55.00% (greater than 440/800 points), and the approximate fixed-sample 95% lower score bound >50%. A direct ON/OFF paired match and longer time control are required before changing any default.

This experiment is a predeclared follow-up to v0.8.3's screening result, not a search over more data. The default remains `StocklessThreats=true` until stronger independent evidence appears. No automatic UCI change, release or stable merge.

Workflow: [v087-threats-off-confirm.yml](../.github/workflows/v087-threats-off-confirm.yml), logs, PGN, decision.json, and report.md in its Actions artifact.