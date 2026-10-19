# Stockless search policy and strength baseline — 2026-10-19

Status: **draft research; no confirmed NPS or Elo gain**.

## Confirmed functional fixes

1. `scripts/run-cutechess-match.sh` assigned duplicate configuration defaults,
   accidentally selecting `StocklessAggression=112`, `StocklessOverdrive=true`
   instead of the engine's UCI defaults `145` and `false`. Corrected, with
   explicit override support, PGN-format official book support, and a
   fake-CuteChess regression test.
2. Linux/Windows CI hard-coded an obsolete UCI identity `v0.7.1`; the
   source currently identifies as `v0.7.2-dev.20261018.2`. The standard
   build CI now reads the expected version from the checked-out source.
3. The **legacy universal release** workflow still embeds older v0.7.1
   packaging/identity expectations and is not fixed by this search PR.
   Standard Linux/Windows/Android compile and smoke CI **all pass**.

## Search refactor in PR #21

`tools/materialize.py` continues to call
`Stockless::compute_threat_signal()` **at the original search-node stage**
before the main move loop.

- For default hybrid (Overdrive OFF), call `make_search_policy()` **after**
  native Stockfish Step 15 pruning rather than before it.
- **Keep policy computation for every surviving move, including first moves
  and shallow depths.** It is *not safe* to skip those solely because they
  appear ineligible for LMR.
- With desktop Overdrive ON, retain the original pre-Step-15 calculation
  since its `pruningDepthBoost` alters native futility/SEE pruning.
- No LMR coefficients, NNUE weights, pruning thresholds, stockfish submodules,
  or UCI default search policy were changed.

### Two rejected hypotheses

- Lazy attack-map computation **combined with skipping the first/shallow
  policy calls** produced 773,262 candidate nodes vs 1,078,618 baseline
  nodes at depth 12. This changed search decisions and failed the
  semantics-preserving equivalence gate.
- Restoring eager attack maps but continuing to skip first/shallow policy
  calls produced the **same mismatch**. Therefore the policy-call skip,
  rather than attack-map timing, caused the regression.

### Corrected PR #21 benchmark

All six interleaved depth-12 bench runs searched exactly **1,078,618
nodes** per engine; fixed CPU target `x86-64-avx2`, 1 thread, 16MiB hash.

Independent same-code runs on hosted CI returned:

| Run | Baseline median NPS | Candidate median NPS | Relative NPS |
| --- | ---: | ---: | ---: |
| First corrected run | 945,248 | 969,548 | +2.57% |
| Repetition 2 | 866,708 | 863,242 | -0.40% |
| Repetition 3 | 1,111,404 | 1,116,004 | +0.41% |
| Repetition 4 | 881,585 | 876,227 | -0.61% |

**Conclusion: no repeatable speed increase has been established**. The
hosted runner variation is larger than the expected effect.

## First live match — pinned Stockfish development version

The original corrected candidate scored **26 W / 126 D / 40 L** in 192
color-paired games vs pinned Stockfish development commit
`0a215d6c9e48856ef630013b8ab8312941a59057`:

- Score 46.354%, estimated -25.38 Elo
- 95% Elo CI -54.12 .. +3.36

This is **not Stockfish 19**; the pinned revision is from September 2026
and later than official Stockfish 19's September 5 release.

## Independent official-book matched games

GitHub Actions: [independent strength run](https://github.com/gaong5247-cmd/Stockless/actions/runs/39266696759).

All engines: `x86-64-avx2`, 1 thread, Hash 32MiB, TC 0.5+0.005,
color-swapped 8-move openings from
`official-stockfish/books@a804a97e709f40aa75a00f9d19e84915b7a3a45c`
(`8moves_v3.pgn.zip`), with an explicit Aggression 145 / Overdrive OFF
for the candidate.

| Opponent | Games | Stockless W/D/L | Score | Relative Elo (95% CI) |
| --- | ---: | --- | ---: | --- |
| Unmodified main Stockless | 512 | 105 / 318 / 89 | 51.562% | +10.86 (-7.66 to +29.38) |
| **Official Stockfish 19**, tag `sf_19` SHA `edb0d9d` | 256 | 35 / 182 / 39 | 49.219% | -5.43 (-28.31 to +17.45) |

These matches are **exploratory**. Both confidence intervals cross
zero. There is no statistically confirmed Elo gain over baseline, and
**Stockless has not been demonstrated to beat official Stockfish 19**.

## Separate PR #22: lazy attack-map hypothesis

[PR #22](https://github.com/gaong5247-cmd/Stockless/pull/22) isolates
delaying attack-map construction *without skipping any policy calls*,
based on this PR. Its initial six-run depth-12 benchmark matched nodes
1,078,618 to 1,078,618, but baseline/candidate median NPS was
904,509 / 904,505 (~0.00%). This is also **not a verified speedup**.
Do not accidentally conflate PR #21 and PR #22.

## Adoption gates

1. Preserve UCI/compilation correctness Linux, Windows and Android.
2. Treat fixed-depth total nodes, PV/signatures and bench as regression
   evidence, *not* a strength proof.
3. Use repeated interleaved NPS tests on controlled hardware, not
   isolated cloud runs.
4. Use independent opening books with paired color swaps, short
   and long time controls, and statistically sound sequential tests
   (SPRT/pentanomial) before promotion.
5. Prefer change-specific A/B tests; compare against official `sf_19`
   separately from pinned development Stockfish.
6. Do not merge these candidate speed tweaks merely on preliminary
   51.56% or +2.57% results.

**Maintain the stable default; leave unproven changes in draft PRs.**
