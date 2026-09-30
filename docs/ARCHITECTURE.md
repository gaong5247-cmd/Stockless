# Stockless architecture

## Rule zero: roles stay separate

Stockless is not a line-by-line 50/50 merge.

### Stockfish-owned runtime
- Position representation and legal move generation
- UCI protocol and options
- Threads / NUMA / transposition table
- Syzygy tablebases
- Iterative deepening, aspiration windows and root management
- Primary NNUE evaluation path

### Reckless-derived research targets
Reckless code remains reference code until a specific idea is ported and independently tested.

Initial targets:
- tactical/threat-aware reduction decisions
- quiet/noisy move ordering differences
- pruning conditions that react to tactical instability
- threat-feature accumulator design
- NNUE output/feature ideas that can cheaply expose tactical pressure

### Stockless-owned policy
`src/stockless/` contains the hybrid policy. It should not know UCI details and should not own the board representation.

The policy returns small search-control signals such as:

```cpp
struct SearchPolicy {
    int pressure;            // 0..256
    int danger;              // 0..256
    int lmrAdjustment;       // negative => search deeper
    int pruningAdjustment;   // negative => prune less
};
```

The first implementation is intentionally deterministic and cheap. NNUE-derived signals can replace/augment it later.

## Integration order

1. Compile the untouched Stockfish baseline.
2. Add `stockless/search_policy.{h,cpp}` without changing decisions.
3. Feed only existing cheap board/search facts into the policy.
4. Wire only LMR adjustment.
5. Run bench + SPRT.
6. Wire pruning adjustment.
7. Run bench + SPRT.
8. Only then prototype a second NNUE signal/head.

This keeps regressions attributable instead of creating an un-debuggable hybrid.
