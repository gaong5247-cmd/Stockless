# Third-party notices

Stockless uses pinned upstream repositories as Git submodules.

## Stockfish
- Repository: official-stockfish/Stockfish
- Pinned revision: 0a215d6c9e48856ef630013b8ab8312941a59057
- License: GNU GPL v3 or later
- Role: C++ engine/search/runtime baseline and primary NNUE evaluator.

## Reckless
- Repository: codedeliveryservice/Reckless
- Pinned revision: 7300f044812d80397960e3a27a4f085e9487419a
- License: GNU AGPL v3
- Role: search and threat-NNUE reference source for deliberate Stockless ports.

Stockless-specific integration code is distributed under AGPL-3.0 so future
Reckless-derived ports can remain under a compatible project-wide copyleft
baseline. Original upstream notices remain authoritative for their code.
