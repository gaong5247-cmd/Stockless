# Stockless deferred search-policy fast path — 2026-10-19

Status: **research candidate; no claimed NPS or Elo gain yet**. Work stays
on a PR until benchmark and match results are reviewed.

## Root causes found

1. `scripts/run-cutechess-match.sh` assigned the same defaults twice.
   The second assignments silently tested **aggression=112 / overdrive=true**
   when the real engine UCI defaults are **aggression=145 / overdrive=false**.
   The arena runner now matches the engine and still supports explicit
   `STOCKLESS_AGGRESSION`, `STOCKLESS_OVERDRIVE`, and `STOCKLESS_THREATS`
   overrides. A mock-CuteChess CLI regression test checks this.
2. CI hard-coded `id name Stockless v0.7.1` while the main source advertises
   `v0.7.2-dev.20261018.2`. Linux/Windows compilation had succeeded, but
   the UCI identity assertion made both jobs fail. Check the version constant
   from `src/stockless/config.h` instead; label produced CI packages
   as development snapshots.

## Proposed semantics-preserving search fast path

`tools/materialize.py` now injects a deferred per-node policy factory.

- The default profile does **not** use `pruningDepthBoost` or
  `reSearchDepthBonus`. Its `lmrAdjustment` matters only after Stockfish's
  Step 15 shallow pruning, and only for depth >= 2 and moveCount > 1.
- Calculate the policy **after** Step 15 for those eligible moves, rather
  than calculating the full policy for moves that are immediately pruned.
- Build the two-side board-derived attack maps lazily, once for each
  node **that actually needs the policy**.
- For opt-in desktop Overdrive, maintain the original early policy timing:
  its `pruningDepthBoost` can affect Step 15. Android/mobile Overdrive has
  no such depth boost and can use the deferred timing.
- Do not change reduction constants, attack-map formulas, NNUE weights,
  default aggression, or Overdrive release defaults.

## Acceptance plan

1. GitHub Actions Linux, Windows, Android UCI and compilation checks pass.
2. `tools/compare_bench.py` compares the PR head against its exact base
   commit, under the same CPU ISA / 1-thread hash 16MiB, with interleaved
   fixed depth 12 and 6 repetitions.
   **Total searched nodes must match** for the semantics-preserving patch.
3. Compare **median NPS** across runs. Small gains are vulnerable to
   noisy GitHub-hosted runners; do not merge solely on a small NPS number.
4. Run the 192-game color-paired CuteChess exploration vs the pinned
   development Stockfish (`0a215d6c...`) using an explicit
   `StocklessAggression=145`, `StocklessOverdrive=false`.
   Same thread, 32MiB hash, 0.5+0.005 each, 32 opening seeds.
5. No positive-Elo claim is possible from that small opening set.
   For a real strength claim, follow with **independent opening suites,
   opening-paired STC and LTC, and sequential SPRT** on controlled hardware.
6. A further separate release-level validation should target official
   **Stockfish 19 (`sf_19`)**, not mistake the pinned September-22
   development Stockfish for that release.

## Potential follow-on candidates (one change per A/B)

- Make board-derived attack features incremental only if proof of
  invariance holds across every legal move and null move.
- Compare policy thresholds (notably shallow cut nodes and
  tactical-volatility filtering) by independent STC/LTC; tune jointly.
- Profile the threat-signal path on both x86-64 and ARM, with PGO
  comparisons on the same ISA and fixed source.
- Compare against official SF19 using genuinely balanced color-swapped
  openings after passing the baseline regression gate.

**Do not move this code to main, change default aggression, or announce
a Stockfish win based only on benchmark NPS or a short arena.**
