# Upstream revisions

Stockless v0.3-dev is pinned to:

- Stockfish master: `0a215d6c9e48856ef630013b8ab8312941a59057`
- Reckless 0.10-dev reference: `7300f044812d80397960e3a27a4f085e9487419a`

## Role split

Stockfish remains the buildable C++ runtime/search/primary-NNUE baseline.

Reckless is a pinned research reference. v0.2/v0.3 specifically study:
- late-move reduction context
- correction-history influence on reductions
- threat accumulator / threat feature representation

Stockless ports ideas deliberately instead of mixing the Rust and C++ engines line-by-line.

Do not silently resync either upstream. Update this file and the materialization patch anchors together.
