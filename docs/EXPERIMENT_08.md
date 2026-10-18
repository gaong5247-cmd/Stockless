# Stockless v0.8 experimental search rebalance — 55% gate

Status: **development candidate, not a strength-verified release**. Stable Stockless v0.7.1 remains unchanged; all changes live in an experimental branch. Neither Stockfish nor Reckless pinned upstream source files have been edited.

## Why these tests

OpenFishtest Community's published W/D/L numbers count the **Challenger's** points. Example: PR #26 contains 36 Challenger wins, 16 draws, 148 Challenger losses, i.e. Challenger 22%, **Stockless 78%**, assuming the PGN results are genuine. These community uploads validate PGN legality and pairing, **not** binary identity, time controls or actual engine execution. They cannot prove Stockless declined or improved in playing strength.

This experiment builds the reference Stockless_v0.7 at commit 261d46be460cb8c83b2d883e8366bcc9d3f09b27 and the current candidate from separate source trees on one GitHub runner with the same x86-64 AVX2 target. Settings: Threads=1, Hash=32 MiB, MoveOverhead=1 ms, ThreatHistory OFF, Overdrive OFF, mobile OFF; color-swapped EPD opening pairs.

## Search candidates

StocklessSearchProfile is a new UCI spin option 0–3, **default 0**.

| Name | UCI changes vs frozen v0.7 | Hypothesis |
|---|---|---|
| HybridOff | StocklessHybrid=false | Stockfish native search may be more efficient |
| Aggression80 | Aggression=80 | Reduce v0.7 LMR buyback overhead |
| Aggression110 | Aggression=110 | Middle-ground search overhead |
| Economy | Profile=1, Aggression=145 | Strong late-quiet savings + tactical-check retention; threat signal at higher depth |
| Defense | Profile=2, Aggression=145 | Restore deepening for dangerous positions; evaluate shallow threats earlier |
| Balanced | Profile=3, Aggression=145 | Moderate quiet pruning economy with forcing-move and emergency prioritization |

None is asserted to be stronger in advance. All bounds stay within the original LMR-reduction budget, and the original Stockfish search, NNUE, TT, PVS, qsearch, SEE, null-move pruning, and other upstream algorithms are retained.

## Evidence gates

tools/v08_strength_gate.py automates six paired fixed-TC screen matches (200 games per candidate), then an independent 800-game holdout of the selected candidate with a different section of the **official Stockfish CC0 opening EPD book**. Color swaps and exact 200/800 game counts are required; crashed, malformed, or missing PGNs abort. The 800-game holdout is **not** used to pick parameters.

Target: **strictly above 55.00% score against v0.7** (more than 110/200 points on a 200-game set). To be *eligible for further study*, the 800-game holdout must also score above 55%, with an approximate 95% interval lower bound above 50%. That interval ignores paired-opening correlation and is NOT official Fishtest SPRT. Before any stable promotion: inspect every crash/time adjudication, re-run independent holdouts, check longer time controls, and conduct a v0.7.1 / Stockfish non-regression test.

**There is no auto-promotion.** Failing or inconclusive tests leave mode 0 and all stable release defaults unchanged.

## How to run

1. Go to the repository's Actions tab, select **v0.8 search strength gate vs frozen v0.7**.
2. Use smoke to confirm compilation, UCI, depth-10 legacy node identity and PGN plumbing: 12 games per candidate + 16 independent games (no Elo claim).
3. Use full for 6 × 200 paired opening games plus 800 holdout, and read the uploaded Stockless-v08-Strength-Gate artifact containing decision.json, report.md, PGNs and logs.
4. To run UCI manually after materialization/build: setoption name StocklessSearchProfile value 3 with StocklessHybrid=true; use value 0 to restore v0.7 policy.

tools/compare_bench.py is also run against frozen v0.7 with profile 0 and must preserve exact depth-limited node counts. Experimental mode speed/strength tradeoffs are tracked separately from CPU-native/PGO builds. Never label a speed result an Elo result.

### Local reproduction (Linux)

    git clone --recurse-submodules -b experimental/v08-adaptive-search-55pct https://github.com/gaong5247-cmd/Stockless.git
    cd Stockless
    python3 tools/materialize.py
    make -C build/stockless-src/src -j2 build ARCH=x86-64-avx2
    c++ -std=c++17 -O2 -Ibuild/stockless-src/src tests/search_policy_test.cpp -o /tmp/search_policy_test
    /tmp/search_policy_test
    python3 tests/uci_history_smoke.py build/stockless-src/src/stockless

See the exact official opening archive and Cute Chess 1.5.1 setup in .github/workflows/v08-strength-gate.yml. Do not compare a native-architecture PGO build against generic AVX2 when attributing results to search-profile logic.
