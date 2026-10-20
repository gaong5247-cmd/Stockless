# Upstream revisions

## Experimental 2026-10-20 SFNNv18 upgrade (NOT a release)

- Stockfish master: `effdc3fd3f6de6e75fe1374a51a7a7eed66f880b` (2026-10-17)
- Reckless 0.10-dev research reference: `7300f044812d80397960e3a27a4f085e9487419a` (unchanged)
- Previous proven-to-build Stockfish pin on stable main: `0a215d6c9e48856ef630013b8ab8312941a59057` (2026-09-22)
- Primary Stockfish network (upstream SFNNv18): `nn-c9e480e92425.nnue`

**This branch is a controlled strength experiment, not a certified faster engine or an official release.**
The `v0.8.9` UCI identity stays untouched for compatibility with the existing release smoke workflows;
do not redistribute experimental binaries under the stable release name.

The Stockfish project publishes tested upstream improvements, but its Elo tests compare upstream
revisions, **not** Stockless with its hybrid policy. We must measure Stockless against its frozen
old-pin baseline and separately against official Stockfish 19. Search node counts may change
when the entire search and NNUE implementation changes; exact-node regression comparisons apply
only to semantically equivalent changes.

Do not silently resync: update this file, `tools/materialize.py` pin, and the actual
`upstream/stockfish` Git submodule gitlink **together**.

## Role split

Stockfish provides the buildable runtime/search/primary-NNUE baseline. Reckless remains
a pinned research reference for LMR, correction history and threat-accumulator ideas;
there is no mixed-NNUE arithmetic or direct Reckless source transplant.
