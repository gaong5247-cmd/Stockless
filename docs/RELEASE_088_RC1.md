# Stockless v0.8.8-rc1 — SFNNv18 + modern dual-slider fastpath

**Pre-release / experimental. No unverified Elo claims.** This branch preserves original Stockfish and Reckless git submodule pins and the Stockless hybrid search infrastructure.

## Changes relative to v0.8.2 modern research build

- Fixed official modern Stockfish SHA `effdc3fd3f6de6e75fe1374a51a7a7eed66f880b`, including **SFNNv18**, K32Q2 features, 32 NNUE layer stacks, int8 feature weights, and the official `nn-c9e480e92425.nnue` network.
- Stockless v0.7 + v0.8 original search functionality retained, including AB/PVS/LMR/history, NNUE, threat-aware depth policy, options and pinned Reckless research reference.
- Only with `STOCKLESS_UPSTREAM_TRACK=modern-v18`, the materializer enables `STOCKLESS_MODERN_DUAL_QUEENS` in *generated* build sources. This collects bishop and rook queen-ray attack maps through modern Stockfish `Attacks::both_attacks_bb`. The older pinned Stockfish source and attack-map routine stay unmodified.
- UCI name is `Stockless v0.8.8-rc1`, and all existing engine option defaults stay conservative (Hybrid true; Aggression 145; Threats true; Overdrive false; ThreatHistory false; SearchProfile 0).
- Builds remain CPU/platform-specific even when provided in per-platform universal ZIPs. Android download is a native UCI binary, **not an APK**.

## Evidence and acceptance gate

Reproducibility workflow: [v088-fastpath-check.yml](../.github/workflows/v088-fastpath-check.yml). It builds frozen modern v0.8.2 and v0.8.8 with identical AVX2 target and compiler, runs policy/history/UCI smoke, compares fixed-depth node counts, then plays 200 opening-paired matches. A matching node count demonstrates that the refactor does not alter search choices for the tested positions; a positive NPS change is still not Elo proof.

**Historical evidence:** v0.8.2 modern SFNNv18 + GCC PGO (Linux AVX2 experiment) scored 289W/297D/214L (54.6875%) against frozen v0.7 on an 800-game holdout. That result cannot be transplanted to a v0.8.8 prerelease build without fresh games, and universal binaries are not the same as single-CPU PGO training.

Do not claim v0.8.8 is stronger than v0.8.2/Stockfish without independent confirmation. If the fastpath fails exact-node parity or makes performance worse, disable it before publishing this experimental release.

## Source build

    git clone --recurse-submodules -b release/v088-rc1-sfnnv18-fastpath https://github.com/gaong5247-cmd/Stockless.git
    cd Stockless
    git -C upstream/stockfish fetch --no-tags --depth 1 origin effdc3fd3f6de6e75fe1374a51a7a7eed66f880b
    git -C upstream/stockfish checkout --detach effdc3fd3f6de6e75fe1374a51a7a7eed66f880b
    STOCKLESS_UPSTREAM_TRACK=modern-v18 python tools/materialize.py
    make -C build/stockless-src/src -j2 build ARCH=x86-64-avx2

The official Stockfish NNUE network is automatically acquired/embedded through its Makefile. This is an upstream-trained network and is not claimed as a separately trained Stockless model.
