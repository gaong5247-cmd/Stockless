# Stockless v0.8.5 — low-weight Threat History experiment

Status: **experimental; no demonstrated improvement, no stable/default changes.**

## Hypothesis

The original v0.7 experimental Reckless-inspired per-Worker `ThreatQuietHistory` keeps a context-specific 2×2 bucket indicating whether the move's origin or destination is threatened. It supplements, but does not replace, Stockfish's normal history/move ordering.

The earlier standalone v0.7 study selected weight 200 from a 160-game screen (55.0%) but **failed independent 800-game confirmation**: 226W/306D/268L, **47.38%**, so v0.7 kept the feature OFF. The weight 50 screen (160 games) returned 50.63%, but was not sufficient evidence of improvement.

In v0.8.2, modern official Stockfish SFNNv18 + GCC PGO scored **54.6875%** vs frozen Stockless v0.7 in a separate 800-game holdout. It is worth checking whether *very small* threat-history weights help this modern baseline without repeating the weak high-weight behavior. No gain is assumed.

## Source and comparison

**Do not change or remove original source:** keep original pinned Stockfish/Reckless gitlinks, Stockless search policy, UCI defaults and all stable releases.

Run one modern SFNNv18/K32Q2 PGO executable (official Stockfish SHA `effdc3fd3f6de6e75fe1374a51a7a7eed66f880b`) against frozen Stockless v0.7 (tag commit `261d46be460cb8c83b2d883e8366bcc9d3f09b27`). All matches use x86-64 AVX2, 1 thread, 32 MiB Hash, same color-swapped book, same clocks and other Stockless parameters (Hybrid=true, Aggression=145, Threats=true, Overdrive=false, Mobile=false, SearchProfile=0).

| Candidate | ThreatHistory | HistoryWeight |
|---|---|---:|
| ModernDefault (control) | OFF | 100 (irrelevant) |
| HistoryW10 | ON | 10 |
| HistoryW20 | ON | 20 |
| HistoryW35 | ON | 35 |
| HistoryW50 | ON | 50 |

These exact candidates were predeclared before v0.8.5 game results.

## Evidence sequence

1. Build frozen v0.7 and the modern PGO candidate from pinned commits.
2. Verify UCI/search smoke and depth-limited identical nodes between non-PGO and PGO when History is OFF.
3. Five candidate screens × 200 paired-color games at 0.2+0.002, on one EPD subset. With the same screening data for all candidates, pick exactly one leading candidate.
4. Run **800 independent holdout games** at 0.4+0.004 on a disjoint subset of the official Stockfish 6mvs_+90_+99 EPD source.
5. The candidate qualifies for a **further independent test** only if its holdout score is strictly above 55.00% vs v0.7 and the approximate fixed-sample 95% interval lower bound is above 50%. Confirmation is not the same as a verified >55% true-strength estimate.
6. Do **not** automatically enable History or release any binaries. A longer-time-control confirmation and preferably direct ON/OFF match against PGO 145 default, on fresh openings, are still necessary.

A partial 200-game lead is only an exploratory result. A negative or inconclusive holdout leaves the original `StocklessThreatHistory=false` default unchanged.

Workflow: [v085-light-history.yml](../.github/workflows/v085-light-history.yml), total full budget **1,800 games**. This workflow saves all PGNs, logs, program identities and results as GitHub Actions artifacts.
