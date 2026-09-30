# Stockless

**Stockless = Stockfish backbone + deliberately ported Reckless ideas + a separate Stockless hybrid policy.**

The project does not blindly average two engines. Upstream code is pinned as submodules so attribution, updates, experiments and regressions stay traceable.

## Current role split

| Component | Owner |
|---|---|
| Board, movegen, UCI, SMP, TT, Syzygy | Stockfish |
| Primary centipawn NNUE evaluation | Stockfish |
| Threat-NNUE/search reference implementation | Reckless |
| Aggression / danger search controller | Stockless |
| Experimental LMR adaptation | Stockless |

Pinned revisions are documented in `docs/UPSTREAM.md`.

## Clone

```bash
git clone --recurse-submodules https://github.com/gaong5247-cmd/Stockless.git
cd Stockless
```

If already cloned:

```bash
git submodule update --init --recursive
```

## Build on Windows

With Python + GNU make/MinGW available:

```powershell
./scripts/build-windows.ps1
```

The script materializes a clean Stockfish working tree under `build/stockless-src/`, overlays the Stockless code, applies guarded integration edits, and builds it.

Manual flow:

```bash
python tools/materialize.py
make -C build/stockless-src/src -j build ARCH=x86-64-avx2
```

## Experimental UCI options

The hybrid controller is **OFF by default**, so the first baseline stays Stockfish-equivalent apart from integration plumbing.

```text
setoption name StocklessHybrid value true
setoption name StocklessAggression value 100
```

`StocklessAggression` accepts 0..200.

Phase 1 only buys back a small amount of LMR depth in forcing/tactically unstable situations. It does not alter the NNUE centipawn score.

## NNUE plan

Current upstream nets:

- Stockfish: `nn-134a887f4c8f.nnue`
- Reckless: `v60-7f587dfb.nnue`

Run:

```powershell
./scripts/fetch-networks.ps1
```

The long-term plan is **not** to evaluate two full networks on every node. Reckless' threat-feature design is used as research input for an eventual Stockless auxiliary attack/danger signal and, if testing supports it, a unified multi-head net.

See `docs/NNUE_PLAN.md`.

## Testing rule

Every change should be isolated:

1. baseline bench
2. one search idea
3. bench / correctness
4. game test / SPRT
5. keep or revert

No giant untestable "engine soup" commits.

## Licensing

Stockfish is GPL-3.0-or-later. Reckless is AGPL-3.0. Their original repositories and license terms remain attached through the pinned submodules. Any copied/ported Reckless-derived code must satisfy its AGPL obligations.
