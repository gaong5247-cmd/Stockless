# Stockless

Stockless is an experimental chess-engine research project that combines a **Stockfish-derived C++ search/runtime base** with selectively ported **Reckless search and NNUE ideas**.

The project deliberately does **not** blend both engines blindly. Responsibilities are separated so every hybrid change can be benchmarked, reverted, and SPRT-tested.

## Architecture

| Layer | Primary source | Role |
|---|---|---|
| Board / movegen / UCI / SMP / TT / Syzygy | Stockfish | Stable runtime and search backbone |
| Main NNUE evaluation | Stockfish | Baseline evaluation and accumulator path |
| Tactical search ideas | Reckless -> ported to C++ | Threat-aware reductions, pruning and move ordering experiments |
| Threat NNUE research | Reckless reference implementation | Threat features / accumulator ideas, not executed directly by the C++ engine |
| Hybrid policy | Stockless | Chooses how aggressively search reductions/pruning should react to tactical volatility |

## Repository layout

- `src/` — buildable Stockfish-derived C++ engine core.
- `src/stockless/` — Stockless-only hybrid search policy.
- `vendor/reckless/` — upstream Reckless source snapshot kept for attribution and porting/reference.
- `docs/ARCHITECTURE.md` — role boundaries and porting plan.
- `docs/UPSTREAM.md` — exact upstream revisions used.

## Phase 0

The first phase keeps Stockfish behavior unchanged by default. Stockless-specific policy is introduced behind an isolated controller before it is wired into pruning/reduction decisions.

Planned sequence:

1. Baseline build + bench signature.
2. Add cheap tactical-pressure features.
3. Wire pressure into LMR only.
4. Test.
5. Wire pressure into pruning only.
6. Test.
7. Prototype NNUE-derived attack/danger signals.
8. Train a dedicated Stockless network only after search-side gains are measurable.

## Build

From `src/`:

```bash
make -j build ARCH=x86-64-avx2
./stockfish bench
```

The binary will be renamed to Stockless as the integration layer lands.

## Licensing

Stockfish is GPL-3.0-or-later. Reckless is AGPL-3.0. Upstream notices and license texts are retained. Code copied or ported from Reckless must continue to satisfy the AGPL-3.0 terms; combined distribution must preserve the applicable copyleft obligations.
