# Stockless v0.8.1 — optional modern Stockfish SFNNv18 evaluation

**Research only. Not a stable release or demonstrated Elo gain.**

## Provenance and preservation

- The repository's Git submodule gitlink remains at official Stockfish commit 0a215d6c9e48856ef630013b8ab8312941a59057 (September 22, 2026). Reckless is still pinned at 7300f044812d80397960e3a27a4f085e9487419a.
- The modern candidate materializer accepts only one other explicit SHA, effdc3fd3f6de6e75fe1374a51a7a7eed66f880b (October 17, 2026), when STOCKLESS_UPSTREAM_TRACK=modern-v18 is set. Without the variable it uses the original pinned version.
- GitHub Actions checks out the modern revision **temporarily in its build workspace**, without changing the committed upstream gitlink. The original source remains available and unmodified in Git.
- The NNUE architecture and network belong to **official Stockfish**. Stockless still adds its own threat signal and search overlay, not a novel trained NNUE.
- In src/stockless/threat_signal.h, the old Position::attacks_by<PAWN> call was replaced with equivalent color-specific pawn_attacks_bb over the same pawn bitboard, because modern Stockfish removed the old accessor. Both old and modern Stockfish provide the bitboard primitive.

## What's new

The modern source contains the newer Stockfish K32Q2 piece-square features, SFNNv18, 32 NNUE layer stacks and the nn-c9e480e92425.nnue network, replacing the pinned September source's original network/architecture. See the official Stockfish [NNUE architecture commit](https://github.com/official-stockfish/Stockfish/commit/5c4cef0bfe61fb3249178b2bcf21f5673557efe7) and [modern source commit](https://github.com/official-stockfish/Stockfish/commit/effdc3fd3f6de6e75fe1374a51a7a7eed66f880b). The official architecture was accepted on Stockfish's own STC and LTC test servers. That does *not* independently validate Stockless strength.

## How to reproduce

1. Clone this experimental branch recursively.
2. Run the optional upstream transition and materialization:

    git -C upstream/stockfish fetch --no-tags --depth 1 origin effdc3fd3f6de6e75fe1374a51a7a7eed66f880b
    git -C upstream/stockfish checkout --detach effdc3fd3f6de6e75fe1374a51a7a7eed66f880b
    STOCKLESS_UPSTREAM_TRACK=modern-v18 python tools/materialize.py
    make -C build/stockless-src/src -j2 build ARCH=x86-64-avx2
    python tests/uci_history_smoke.py build/stockless-src/src/stockless

3. To restore the pinned base when working locally:

    git -C upstream/stockfish checkout --detach 0a215d6c9e48856ef630013b8ab8312941a59057
    python tools/materialize.py

4. Read build/stockless-src/STOCKLESS_MATERIALIZED.txt to confirm the provenance.

## Test design and initial outcomes

The dedicated workflow is .github/workflows/v081-modern-upstream.yml. It builds frozen Stockless v0.7 and the modern candidate with the same compiler/AVX2 target, equal Threads=1/Hash=32, independent official Stockfish EPD opening subsets and two-color repeated matches.

- Candidate presets: ModernDefault, HybridOff, Aggression110, Aggression175, Balanced.
- Smoke: each 12 games plus a fresh 16-game confirmation; validates engine integration but **cannot support a playing-strength conclusion**.
- Full: five 200-game screening matches + independent 800-game holdout of the best observed candidate = **1,800 games**.
- Target: strictly above 55% against frozen Stockless v0.7 on 800-game holdout and approximate fixed-sample 95% interval lower bound above 50%. Additional long TC or SPRT would be needed for any release.
- No configuration is promoted automatically. Existing stable Stockless v0.7.1 and its Windows/Linux/Android artifacts are not modified.

The successful initial smoke run is [GitHub Actions #39115090333](https://github.com/gaong5247-cmd/Stockless/actions/runs/39115090333). Its CI log demonstrates that the modern nn-c9e480e92425.nnue network was downloaded/validated and a real modern-engine match completed.

**Do not advertise a gain in playing strength unless a large independent match actually demonstrates it.**
