# Stockless v0.8.3 — PGO + Search Aggression Fine-Tuning (research only)

**Status:** Experimental only. **No playing-strength gain beyond v0.8.2 has been established.** No stable release, default, main branch or pinned upstream submodule is changed.

## Current verified comparison

In [v0.8.2 full Action run #39116335655](https://github.com/gaong5247-cmd/Stockless/actions/runs/39116335655), the identical-source PGO build searched the same 723,200 depth-limited nodes and measured 9.27% higher median NPS on that runner, relative to the ordinary AVX2 build. This does not by itself establish an Elo gain. In an independent 200-game PGO-vs-non-PGO match, PGO scored 68W/58D/74L = 48.50% (inconclusive).

Combined **modern SFNNv18 + PGO vs frozen Stockless v0.7**:

| Phase | Games | W / D / L | Score | Elo difference |
|---|---:|---|---:|---:|
| Screen | 200 | 83 / 51 / 66 | 54.25% | +29.60 |
| Independent holdout | 800 | 289 / 297 / 214 | **54.6875%** | **+32.67** |

The approximate fixed-sample 95% Elo CI for the holdout was [+13.61, +51.92] (opening-pair correlation excluded). The >55% target was NOT met. A PGO-specific Elo effect cannot be inferred by comparing separate matches.

## Frozen source and experiment setup

Keep:

- Stockless code and original pinned Stockfish/Reckless Git submodules.
- Modern optional materialized Stockfish source at exact SHA effdc3fd3f6de6e75fe1374a51a7a7eed66f880b (October 17, 2026).
- SFNNv18/K32Q2 evaluation and Stockless hybrid search integration.
- x86-64-avx2 CPU target, one thread, 32 MiB Hash, MoveOverhead 1 ms, identical PGO training compilation for **all** tuning candidates.

Only UCI parameters differ. All candidates share the *same compiled PGO executable* and are evaluated against a separately built, frozen Stockless v0.7 binary.

## Predeclared candidates

| Configuration | Aggression | Board threat signals | Overdrive |
|---|---:|---|---|
| ModernDefault (control) | 145 | On | Off |
| Aggression135 | 135 | On | Off |
| Aggression140 | 140 | On | Off |
| Aggression150 | 150 | On | Off |
| Aggression155 | 155 | On | Off |
| Aggression160 | 160 | On | Off |
| Overdrive145 | 145 | On | On |
| ThreatsOff145 | 145 | Off | Off |

ThreatHistory stays off, SearchProfile=0, mobile profile off, Hybrid on for all eight candidates. These settings were chosen before seeing v0.8.3 game results. We do not claim that any setting is stronger.

## Gating and publication

[Dedicated GitHub Actions workflow](../.github/workflows/v083-aggression-tune.yml):

1. **Smoke** — build frozen v0.7 and modern PGO binaries; deterministic depth-11 normal/PGO node-count checks; C++/UCI smoke; 12 games for each configuration plus 16 holdout games. Smoke scores are NOT Elo proof.
2. **Full screening** — eight configurations × 200 games, opposite colors paired, using the same official Stockfish CC0 EPD screen set, time control 0.2+0.002.
3. **Independent confirmation** — select exactly one best screening configuration and play 800 games against frozen v0.7 on a separate, non-overlapping EPD confirmation set, time control 0.4+0.004.
4. Only regard a candidate as eligible for additional work if the independent holdout scores **strictly above 55.00%** and the approximate 95% score interval lower bound is above 50%. A repeat under longer time control and fresh seeds is needed to establish a reliable lasting advantage. *Never* automatically change defaults or publish a release.
5. Inspect the PGN, time forfeits, crashes, source SHAs, logs and exact UCI settings before interpreting results.

Official EPD archive SHA-256 and run artifacts are recorded. Note: the new 20261022 shuffle seed makes screening and holdout disjoint within this experiment, but previous studies of the same opening-book archive may have some overlapping positions. Do not treat repeated positive screens as independent confirmations.

### Expected full workload

8 × 200 + 800 = **2,400 games**. The result is a controlled comparison, not an official CEDR, CCRL or Fishtest rating.

The original default is preserved until a candidate genuinely passes independent strength verification. If all eight fail, none will be promoted.