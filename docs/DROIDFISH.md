# DroidFish / Android

Stockless v0.7.1 is built as a normal Android UCI executable, so DroidFish can run it directly.

## Supported artifacts

GitHub Actions builds two binaries:

- `stockless-v0.7.1-arm64-v8a` — recommended for almost every modern 64-bit Android phone/tablet.
- `stockless-v0.7.1-armeabi-v7a` — fallback for old 32-bit ARM devices.

Both are compiled with Android API 26-compatible NDK toolchains (Android 8+ target).

The Stockfish NNUE used by the C++ core is embedded into the executable during the normal build, so no separate `.nnue` file is required for the default setup.

## Install in DroidFish

1. Download the matching Stockless artifact from the latest successful GitHub Actions build.
2. Copy the executable into:
   `DroidFish/uci/`
3. In DroidFish open:
   **Left drawer -> Manage Chess Engines -> Select Chess Engine**
4. Select the Stockless binary.
5. Optional tuning is under:
   **Manage Chess Engines -> Set options**

DroidFish copies the selected engine to its private executable directory, marks it executable, and launches it as a UCI process.

## Stockless options

- `StocklessHybrid = true` — enables Stockless hybrid search.
- `StocklessAggression = 0..200` — 145 is the default.
- `StocklessThreats = true` — enables the v0.3 tactical threat signal.
- `StocklessMobile = true` — enabled by default on Android builds.
- `StocklessOverdrive = false` — selective tactical extension is opt-in.
- `StocklessThreatHistory = false` — OFF following v0.7 tournament testing.
- `StocklessHistoryWeight = 100` — inactive when history is OFF.

The mobile profile delays the more expensive threat-map calculation to deeper/important nodes and caps LMR depth buyback more aggressively.

## Suggested DroidFish preset

For a phone:

```text
StocklessHybrid = true
StocklessAggression = 145
StocklessThreats = true
StocklessOverdrive = false
StocklessThreatHistory = false
StocklessMobile = true
Threads = 2-4
Hash = 64-256
```

For tablets, adjust threads and hash according to measured sustained performance; v0.7's default aggression remains 145.

## Architecture

v0.2:
- moves the hybrid adjustment to the end of Stockfish's LMR calculation
- uses Reckless 0.10-dev ideas such as correction-history sensitivity
- preserves Stockfish's cut-node behavior unless the position is forcing

v0.3:
- adds `AttackPressure`, `KingDanger`, and `TacticalVolatility`
- derives them from Stockfish bitboards/attack maps
- uses them to decide when to buy back search depth
- does not run a second full NNUE at every node

This is the bridge toward a future dedicated Stockless multi-head NNUE.
