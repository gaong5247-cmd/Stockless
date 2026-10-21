# Experiment: factor node-invariant policy arithmetic (v0.8.9)

This branch is isolated from PRs #28 and #29 and based on the exact released Stockless v0.8.9. **Not approved for the stable build.**

## Hypothesis

The existing \`make_search_policy()\` recomputes the same king danger, baseline volatility, tactical flags, and policy caps for every candidate move that survives the native Stockfish pruning stage. A single node may examine multiple moves, so preparing immutable values once *might* save work. It can also make performance worse for nodes with no surviving moves: this is explicitly a **benchmarkable hypothesis**, not a guaranteed optimization.

## Changes

- \`SearchNodeInputs\` and \`PreparedSearchPolicy\` hold static per-node features.
- \`prepare_search_policy\` runs once at the existing move-loop boundary. Both default and optional desktop Overdrive then use \`make_prepared_move_policy\` per surviving move.
- Crucially, \`beta - alpha\` and \`(ss + 1)->cutoffCnt\` are **not cached**: both can change after recursive searches of preceding moves. They remain per-move arguments, alongside move count, capture and check flags.
- \`make_search_policy\` remains as a compatibility wrapper using the same implementation.
- No UCI changes, no NNUE changes, no heuristic constants, no pruning stage/timing changes, no changes to Stockfish/Reckless pins.
- Regression tests compare against the frozen pre-refactor v0.7 policy for **100,000 random inputs** and **200,000 prepared-move evaluations**, including reusing the same node state with changed alpha-window/cutoff/move flags.

## Adoption checks

1. Linux/Windows/Android materialization and build/UCI must pass.
2. In \`optimization-benchmark\`, baseline and candidate depth-12 nodes must exactly agree for all six AB/BA interleavings; otherwise the refactor is **rejected as a semantics-preserving optimization**.
3. Compare median NPS with at least 20 rounds on fixed local CPUs, including mobile/Overdrive-on profiles where appropriate. If no reproducible throughput gain is found, remove this experiment instead of adding complexity.
4. Existing 512 paired-color games vs untouched baseline and 256 vs official SF19 are exploratory. Use more games and STC/LTC if search decisions unexpectedly change. Speed does not prove Elo gains.
5. Keep this branch/PR draft until checks are complete. Do not merge into \`main\` automatically.
