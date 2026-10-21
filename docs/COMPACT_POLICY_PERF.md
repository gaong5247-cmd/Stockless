# Compact SearchPolicy return value (v0.8.9)

**Research-only performance candidate. Stable source, UCI defaults, and playing decisions unchanged.**

## Identified dead hot-path output

The v0.8.9 `SearchPolicy` struct returned six `int` fields (24 bytes): `pressure`, `danger`, `volatility`, `lmrAdjustment`, `pruningDepthBoost`, `reSearchDepthBonus`. The first three fields were used **only internally** when constructing policy decisions. The patched native Stockfish search consumes only the final three. This experiment keeps bounded pressure/danger/volatility as local variables and returns only the three needed values (12 bytes).

On conventional Linux x86-64 SysV ABI, 24-byte aggregates generally require an indirect/sret return, while 12-byte integer aggregates can be returned in registers. This might save stack traffic in a search's per-move policy call. Windows x64 and AArch64 ABI behavior differs, so platform-specific measurements are required. Optimizing compilers might already scalar-replace or inline the original return, in which case no gain should be expected.

## Invariance

- Same source operands, evaluation order, clamps, constants, LMR, pruning boost and re-search boost.
- The frozen v0.7 independent policy reference remains in `tests/search_policy_test.cpp`, adjusted only to compare the three search-consumed fields.
- `static_assert(sizeof(SearchPolicy) == 3*sizeof(int))` detects accidental output growth.
- No UCI option or search-policy configuration change. No upstream source or NNUE network change.
- Fixed-depth node counts must exactly match; any mismatch blocks merge.

## Performance gates

The `optimization-benchmark` Actions job compares current candidate with exact v0.8.9 using interleaved AB/BA at depth 12. Demand repeated fixed-target hardware, multiple depths and CPUs before claiming an NPS gain; require official opening book color-paired STC and LTC to check strength non-regression. A single CI run or >50% short match is insufficient.

If there is no stable NPS increase, prefer reverting to the simpler current design rather than merging a cosmetic change.
