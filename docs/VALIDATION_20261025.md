# Stockless v0.9.0 predeclared validation plan and completed results

**Original experiment: not approved. Separate final replication: passed and
published as [Latest Stockless v0.9.0](https://github.com/gaong5247-cmd/Stockless/releases/tag/Stockless_v0.9.0).**

The PGO validation completed in
[Actions run 40153018357](https://github.com/gaong5247-cmd/Stockless/actions/runs/40153018357)
using candidate source `1f1a4870fb02cc6cd04d52e2e082ef72aed0ff46`.
The shorter-time-control confirmation passed, but the longer-time-control
confirmation did not establish a positive gain at the predeclared confidence
threshold. Both were required, so that run did not approve or publish v0.9.0.

A separate [final longer-time-control replication protocol](LONG_REPLICATION_20261025.md),
`20261025-long-replication-99`, was predeclared after reviewing these results and
completed in [Actions run 40156434508](https://github.com/gaong5247-cmd/Stockless/actions/runs/40156434508).
Its 8192 fresh games passed the two-sided 99% paired lower-bound requirement, and
the unchanged original short result still passes. The final match report is
**valid and approved**. It does not pool the old longer sample or revise this
experiment's failed gate. Multi-platform builds and package checks passed, and
v0.9.0 was published as Latest on **2026-10-25 at 04:18:36 UTC**. The release
includes the [actual final JSON report](https://github.com/gaong5247-cmd/Stockless/releases/download/Stockless_v0.9.0/validation-report.json)
and the [original not-approved report](https://github.com/gaong5247-cmd/Stockless/releases/download/Stockless_v0.9.0/prior-report.json).

Baseline is the immutable source commit
`d2e165a6ab70a9a00e1d52ba2a0f4f678ffef22f`, published as Stockless v0.8.9.
Candidate and baseline were built once on the same runner with the same GCC,
fixed AVX2 target, pinned upstream source and NNUE. The candidate used verified
PGO; the baseline used ordinary optimization. The identical binary artifacts
were reused in every shard. The tested candidate is the exact commit above,
not a later documentation commit.

## Candidate rationale

The earlier lean/prepared candidate (`5254c4a`) is reused, rather than reimplementing
already-tested cleanup. This candidate additionally fixes three concrete defects:
pin ownership was reversed, prepared policy cached mutable depth, and the mobile
Overdrive cap remained active despite its other features being disabled. Changing
pin ownership changes search behavior; baseline node equality is not expected for
the complete candidate.

## First candidate result and compiler follow-up

The ordinary-build candidate `b418ca42e3c33508aad625ad8ca21d3687a88135` completed
its 512-game screen at 72W/354D/86L, 48.633%, −9.50 Elo with a pair-level 95% interval
[−24.92,+5.88]. It failed screening and did not run confirmation or publish.
[Full Actions evidence](https://github.com/gaong5247-cmd/Stockless/actions/runs/40151375797).
This bundled result does not isolate whether any individual source fix helped or hurt.

The second candidate changes the compilation strategy to verified PGO. It is not
a rerun of the same executable. Its screening and confirmation positions all come
from fresh ranges. The measured results apply only to the exact tested Linux PGO
binary. The publication workflow was designed to reuse those bytes only after
approval; the original run did not publish. No strength gain is established for
companion builds.

Local verification on the exact corrected source found clean PGO +1.77% median NPS
versus ordinary compilation, identical 2,465,981 nodes and 51 bestmoves at depth 14
in 3 interleaved repetitions. An earlier purported PGO executable retained
instrumentation and was excluded; the corrected process forces every object to
recompile and verifies that no profiling symbols remain. The unexplained partial
cleanup is not attributed to an upstream defect. Local timing is not Elo evidence.

## Completed original PGO validation

All planned games completed and the evidence passed the game, pairing, identity
and fault checks. The counts below are candidate wins/draws/losses. Elo intervals
use opening pairs and the approximate method declared before the matches.

| Stage | Time control | Games | W / D / L | Candidate score | Relative Elo | Pair 95% Elo interval | Decision |
|---|---|---:|---|---:|---:|---|---|
| Screen | 1+0.01 | 512 | 84 / 369 / 59 | 52.441% | +16.98 | [+2.21, +31.81] | Eligible for confirmation only |
| Short confirmation | 2+0.02 | 4096 | 373 / 3434 / 289 | 51.025% | +7.13 | [+3.20, +11.06] | Passed |
| Longer confirmation | 5+0.05 | 1024 | 51 / 932 / 41 | 50.488% | +3.39 | [−2.40, +9.19] | Inconclusive; did not pass |

The short confirmation met both requirements: positive lower confidence bound
and point Elo of at least +5. The longer confirmation had a positive point
estimate, but its interval included zero. This is not evidence of a confirmed
regression; it is insufficient evidence for the required longer-time-control gain.
The original release gate therefore returned **not approved** and remains false.

The screen is excluded from the confirmation statistics, and the two confirmation
time controls are reported separately. The earlier ordinary-build screen remains
recorded above and is not pooled with this different executable. None of these
bundled results isolates the effect of the pin fix, policy cleanup or PGO alone.
They compare the tested Linux AVX2 PGO candidate with a freshly compiled ordinary
AVX2 v0.8.9, not with the previously downloadable universal binary.

## Completed final replication

The separate final run reused the identical candidate and baseline binaries from
run 40153018357. It played all 8192 newly allocated games, passed the integrity
checks, and returned `valid: true`, `approved: true` under
`20261025-long-replication-99`. The selected confidence level for the new longer
sample is **99%**, as declared before those games. The exact figures are in the
[final JSON report](validation/v0.9.0-final-long-20261025.json); the
[original not-approved report](validation/v0.9.0-pgo-20261025.json) is preserved.

| Stage in final report | Time control | Games | W / D / L | Candidate score | Relative Elo | Selected pair interval | Decision |
|---|---|---:|---|---:|---:|---|---|
| Original short confirmation, reused | 2+0.02 | 4096 | 373 / 3434 / 289 | 51.025391% | +7.126143 | 95%: [+3.195154, +11.058957] | Passed unchanged |
| New final longer replication | 5+0.05 | 8192 | 435 / 7399 / 358 | 50.469971% | +3.265787 | 99%: [+0.581509, +5.950455] | Passed |

The final engine source is `1f1a4870fb02cc6cd04d52e2e082ef72aed0ff46`; the
orchestrator revision is `4a9c1e55b2ed28c993261d3cdea671e90d823c2f`. These are
different identities. The tested baseline is v0.8.9 rebuilt using ordinary
optimization with the same compiler and fixed AVX2 target. The measured gain is
modest and applies to that exact Linux PGO comparison.

This series played **14336 actual games**: 512 in the ordinary-build screen,
512 in the PGO screen, 4096 in the original short confirmation, 1024 in the
original longer confirmation, and 8192 in the final replication. Reusing the
short result does not add another 4096 games. Neither the old longer result nor
the screens enter the new longer estimate; the two time controls remain separate.

This was the final attempt; no additional candidate or match attempt follows in
this series. The new 99% interval is not a global 99% guarantee. The approximate
nominal one-sided union bound across the two longer testing opportunities is 3%,
with the assumptions and selection limitations documented in the final protocol.

## Original frozen experiment

| Stage | Games | Time control | Distinct starting positions | Purpose |
|---|---:|---|---:|---|
| Screen | 512 | 1+0.01 | 256 | Continue only if complete, fault-free and score >=50% |
| Short confirmation | 4096 | 2+0.02 | 2048 | Pair 95% lower Elo bound >0 and point Elo >=+5 |
| Longer confirmation | 1024 | 5+0.05 | 512 | Pair 95% lower Elo bound >0 |

All games use one search thread, Hash 32 MiB, identical retained UCI settings,
two concurrent games per runner and CuteChess 1.5.1. Each opening is played with
colors swapped. Draw adjudication: move 40 / count 8 / 8 cp; resignation: count 3 / 650 cp.
Recovery mode is disabled. No candidate parameter tuning follows the screen.
Under this original plan, both confirmation stages had to pass, with no assessment
at intermediate game counts or retries until favorable. The separate final
replication is explicitly a later protocol with a larger fresh sample and stricter
confidence threshold; it does not turn the original plan into a successful test.

Official Stockfish `8moves_v3` is pinned to books commit
`a804a97e709f40aa75a00f9d19e84915b7a3a45c`. Unique legal positions are sorted,
shuffled once with seed 20261025, and split at opening offsets 2816, 3072, 5120. The screen
and both confirmation stages have no overlapping starting positions. PGNs,
logs, commands, binaries, book hashes and exact source SHAs are retained as Actions
artifacts. The gate checks legal movetext, completed results, expected game counts,
pair colors, matching FENs, unique openings, consistent hashes and absence of
engine/connection/time faults. Incomplete evidence is an error, not a loss or draw.

Confidence intervals use pair means as observations, not independent individual
games. The report includes pentanomial pair outcomes. This is a fixed-sample test,
not SPRT; the normal interval is approximate and measured effects are specific to
these conditions. Near-zero findings remain inconclusive. No Stockfish 19 victory
or platform-independent rating follows from this test.

## Publication

Publication is disabled on ordinary main/version pushes. The reusable universal
build can publish only when called by the successful gate, then rechecks an approved
report for its exact candidate commit, fixed baseline, both planned samples and
positive intervals. All seven ZIP packages must pass manifest, identity and hash
checks. Existing tags/releases are never overwritten. The original completed run
did not meet its longer-confirmation threshold, so its publication was skipped.
The separate final protocol passed the match gate; platform builds, package checks
and publication then completed successfully. The
[v0.9.0 release](https://github.com/gaong5247-cmd/Stockless/releases/tag/Stockless_v0.9.0)
is now Latest, with seven platform ZIPs, checksums, the final JSON and Markdown
reports, and the original not-approved JSON report: eleven assets in total.

Publication preserves both decisions in its evidence. The engine source/tag target is
`1f1a4870fb02cc6cd04d52e2e082ef72aed0ff46`; the newer workflow/protocol commit is
recorded separately as `4a9c1e55b2ed28c993261d3cdea671e90d823c2f`. No additional
release attempt follows this final protocol.
