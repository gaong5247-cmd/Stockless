# NNUE role split

Pinned upstream networks at bootstrap:

- Stockfish primary net: `nn-134a887f4c8f.nnue`
- Reckless reference net: `v60-7f587dfb.nnue`

## Phase 1 — one evaluator, two research sources

The executable uses the Stockfish NNUE path as the **only score-producing evaluator**.

Reckless' network is not averaged into the score. Its source is retained to study:

- threat accumulator updates
- threat feature indexing
- sparse/vectorized forward pass
- output bucket design
- incremental refresh rules

Why: blindly averaging two unrelated NNUE outputs mixes calibration scales and doubles inference cost without proving search strength.

## Phase 2 — threat signal prototype

Add a Stockless-owned auxiliary signal with a tiny output contract:

- `attackPressure: 0..256`
- `kingDanger: 0..256`
- `tacticalVolatility: 0..256`

Those signals adjust search policy, not centipawn evaluation.

## Phase 3 — unified Stockless network

Only after search experiments survive SPRT:

1. Generate positions from strong self-play / mixed-engine games.
2. Keep a normal value target.
3. Add auxiliary attack/danger targets.
4. Train shared features with multiple heads.
5. Benchmark NPS loss.
6. Accept only if playing strength improves.

The long-term goal is one efficient network, not two full NNUEs evaluated on every node.
