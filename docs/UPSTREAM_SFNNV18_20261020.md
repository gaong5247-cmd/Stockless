# Experimental Stockless upstream modernization — 2026-10-20

**Status: unverified candidate; NOT stronger until tested.**

## Why this experiment

Stockless main v0.8.9 pins Stockfish `0a215d6c9e48856ef630013b8ab8312941a59057` (September 22, 2026).
Official Stockfish master subsequently advanced through SFNNv18 and the
`nn-c9e480e92425.nnue` evaluation network, plus changes to threat
feature updates, move generation and search.
This branch pins Stockfish `effdc3fd3f6de6e75fe1374a51a7a7eed66f880b` (October 17, 2026)
while retaining the same Stockless policy code and experimental Reckless reference.

Official Stockfish's public regression data measures upstream Stockfish strength;
it does **not** predict the Elo of Stockless without controlled matches.

## Files changed

- `upstream/stockfish`: one Git **submodule pointer** to the new master commit.
- `tools/materialize.py`: synchronized strict SHA verification; do not disable pin checks.
- `docs/UPSTREAM.md`, `docs/NNUE_PLAN.md`: synchronized evidence trail.
- `optimization-bench.yml`: strict node count equivalence is meaningful only if
  both engines share the same Stockfish source. On upgrade PRs, report the nodes and NPS
  but **do not** reject expected search changes or claim speedup from their NPS ratio.
- `tools/compare_bench.py`: prominent warning for comparisons of different trees.

## Required gates before accepting into main

1. `tools/materialize.py` must apply every patch anchor exactly once to the new upstream.
2. Linux and Windows compile + UCI smoke + search policy and history tests pass.
3. Android arm64 and armv7 compile. Universal builds and embedded new NNUE succeed.
4. Use identical CPU instruction set, hash, Threads=1, MoveOverhead and time control.
5. Use color-swapped independent opening pairs, e.g. official Stockfish books.
   Run candidate vs **unmodified Stockless v0.8.9** first, then vs official Stockfish 19.
6. Treat first 512/256 quick games as *exploration* only. Follow with
   controlled-hardware STC and LTC sequential (SPRT/pentanomial) tests.
7. If a gate fails, leave the code in this experimental branch and do **not** publish
   a release or claim an Elo improvement.

## Separation of confounders

This upgrade changes both upstream search and NNUE; it cannot tell which one
individually caused a strength change. If promising, run a second matrix:
new upstream with StocklessHybrid OFF vs the same upstream with hybrid ON,
and compare each to the old-pin baseline. Keep other UCI settings unchanged.

References:
- Stockfish commit: https://github.com/official-stockfish/Stockfish/commit/effdc3fd3f6de6e75fe1374a51a7a7eed66f880b
- Stockfish 19 baseline: https://github.com/official-stockfish/Stockfish/releases/tag/sf_19
- Stockfish regression testing: https://official-stockfish.github.io/docs/stockfish-wiki/Regression-Tests.html
