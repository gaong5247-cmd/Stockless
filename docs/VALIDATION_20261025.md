# Stockless v0.9.0 predeclared validation plan

Baseline is the immutable source commit
`d2e165a6ab70a9a00e1d52ba2a0f4f678ffef22f`, published as Stockless v0.8.9.
Candidate source is the exact commit of the Actions run. Candidate and baseline
are built once with the same runner, GCC and fixed AVX2; candidate uses verified PGO,
baseline uses ordinary optimization,
upstream source and NNUE. The identical binary artifacts are reused in every shard.

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
from fresh ranges. Only the exact tested Linux PGO binary can carry the measured
strength claim; it is reused byte-for-byte in the release, while companion builds
remain clearly labeled.

Local verification on the exact corrected source found clean PGO +1.77% median NPS
versus ordinary compilation, identical 2,465,981 nodes and 51 bestmoves at depth 14
in 3 interleaved repetitions. An earlier purported PGO executable retained
instrumentation and was excluded; the corrected process forces every object to
recompile and verifies that no profiling symbols remain. The unexplained partial
cleanup is not attributed to an upstream defect. Local timing is not Elo evidence.

## Frozen experiment

| Stage | Games | Time control | Distinct starting positions | Purpose |
|---|---:|---|---:|---|
| Screen | 512 | 1+0.01 | 256 | Continue only if complete, fault-free and score >=50% |
| Short confirmation | 4096 | 2+0.02 | 2048 | Pair 95% lower Elo bound >0 and point Elo >=+5 |
| Longer confirmation | 1024 | 5+0.05 | 512 | Pair 95% lower Elo bound >0 |

All games use one search thread, Hash 32 MiB, identical retained UCI settings,
two concurrent games per runner and CuteChess 1.5.1. Each opening is played with
colors swapped. Draw adjudication: move 40 / count 8 / 8 cp; resignation: count 3 / 650 cp.
Recovery mode is disabled. No candidate parameter tuning follows the screen.
Both confirmation stages must pass; the result is not assessed at intermediate
game counts and the experiment is not repeated until favorable.

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
checks. Existing tags/releases are never overwritten. Failure leaves Latest at
v0.8.9 and preserves the candidate and evidence for review.
