# STOCKLESS — Intel XPU Aggressive NNUE (experimental)

**Scope:** Custom training system, NOT official `nnue-pytorch`. The engine uses
**the same pinned Stockfish NNUE architecture, feature transformer, CPU evaluator
and `.nnue` file layout**. Our trainer changes **only FC2, the eight
128-input output-layer vectors and biases**. This is a last-layer conversion,
**not** a full 10-million-position feature-transformer retrain and not a new
architecture. Never replace the shipped default NNUE without match testing.

Pinned implementation:
- Stockfish commit `0a215d6c9e48856ef630013b8ab8312941a59057`
- `HalfKAv2_hm + FullThreats + PP_3Wide`, 8 output buckets, `1024 → 32 → 32 → 1`
- Final-layer numerical output remains the upstream Stockfish code
- The training command will **stop** rather than silently use CPU if
  `torch.xpu.is_available()` is false.

## Prerequisites (Windows 11)

Use Python 3.10+ with your functioning Intel XPU-enabled PyTorch. Verify first:

```powershell
python -c "import torch; print(torch.__version__, torch.xpu.is_available(), torch.xpu.get_device_name(0) if torch.xpu.is_available() else 'NO XPU')"
python -m pip install numpy python-chess
```

The XPU build/driver must be compatible; this repo does not attempt to overwrite
a working `torch` environment. Build tools: git, Python, MSYS2/MinGW make/C++.

### 1. Native Stockfish feature extraction

From Stockless repository root:

```powershell
powershell -ExecutionPolicy Bypass -File tools/xpu_nnue/build_probe.ps1
```

**Do not run `scripts/build-windows.ps1` after this:** it wipes the
instrumented materialized source. The probe adds only a debug command and
does **not** alter the original NNUE inference or compressed `.nnue` format.

Check the probe manually (run the compiled `stockless.exe` under
`build/stockless-src/src`, or the binary name produced by your toolchain):

```
uci
isready
position startpos
stockless_features
quit
```

Expected line begins `stockless_features` followed by bucket, raw PSQT,
skip contribution, raw network evaluation and exactly 128 comma-separated
`uint8` values. The preprocessing stage independently recomputes the native
raw output from the original `.nnue` last layer and **rejects mismatches**.

### 2. Generate fully labelled CSV

Use a known working **Stockfish teacher executable**, which can be different
from the instrumented STOCKLESS probe:

```powershell
python tools/xpu_nnue/generate_csv.py --engine "C:\\Engines\\stockfish.exe" --out data/stockless_teacher.csv --target-positions 10000000 --depth 12 --threads 2
```

For 8 million positions use `--target-positions 8000000`.
The generator runs actual self-play, deliberately varies near-best moves,
requests `UCI_ShowWDL`, and stores:

`game_id, ply, fen, score_cp, mate, wdl_win, wdl_draw, wdl_loss,
depth, nodes, best_move, pv, attack_pressure, king_danger,
game_result, actual_result_stm, teacher`.

Important:
- `wdl_win/draw/loss` are **Stockfish estimated WDL per mille (sum 1000)**.
- `actual_result_stm` is an **observed result** only for finished games;
  unfinished games are `game_result=*` with no actual result.
- `score_cp` is the searched score in **side-to-move perspective**;
  mate scores are in the separate `mate` field.
- This could take a long time at high depth; no positions are pre-generated
  by this repository change.
- Large data files belong in `data/`, not in Git.

### 3. Prepare a streaming CPU → XPU dataset

Specify the same original NNUE file that the **instrumented STOCKLESS** loads:

```powershell
python tools/xpu_nnue/prepare.py --csv data/stockless_teacher.csv --probe "build/stockless-src/src/stockless.exe" --net "build/stockless-src/src/nn-134a887f4c8f.nnue" --out data/prepared
```

If your pinned build uses another default network, pass its real file path;
do not rename a foreign network to bypass validation. The input network must
match the pinned architecture exactly.

The preprocessing stage:
- validates FEN and estimated WDL
- de-duplicates identical EPD positions across **all** splits on disk (SQLite)
- splits by **game ID** into 90% train / 5% val / 5% test (approximately)
- extracts the original Stockfish FC2 inputs by native code
- stores compact **157-byte/position** records in `train.bin`,
  `val.bin`, `test.bin`

At 10 million *retained unique* positions the binary records occupy about
**1.57 GB**, in addition to CSV and the de-duplication database. This number
does not include data rejected as mate/duplicate. Use a **fresh output folder**
for each full preprocessing attempt; partial runs are not resumed yet.

### 4. Train continuously on Intel XPU

```powershell
python tools/xpu_nnue/train_xpu.py --base-net "build/stockless-src/src/nn-134a887f4c8f.nnue" --data data/prepared --out training_runs/stockless_xpu --batch-size 2048 --save-every 500 --attack-cp 8
```

The trainer starts with real original **quantized FC2 weights**. It uses custom
PyTorch/XPU operations to train only that layer, with:
- conservative Stockfish searched-score anchoring (`--teacher-mix` defaults 0.08)
- a bounded attacking-position preference, guarded by teacher WDL and
  teacher score; aggressive positions are **not assumed correct**
- a penalty for moving too far from original weights
- float optimizer on XPU and **int8 FC2 / int32 bias** quantization on export
- validation checkpoints; automatic `latest.pt` / `latest.nnue`,
  `best.pt` / `best.nnue`
- **unlimited epochs until Ctrl+C**; interruption after minibatch saves model
  and optimizer states. Restart the same command to resume.

Avoid closing PowerShell by force; `Ctrl+C` is the supported clean stop.
Unexpected power failure can lose steps since the previous checkpoint.

### 5. Test an exported NNUE in a real engine

The parser is restricted to the pinned format, and its **byte-preserving**
test checks that only eight final layers changed. A synthetic unit test alone
**does not prove Stockfish will load the model**. Use the real engine:

```
uci
setoption name EvalFile value C:\absolute\path\to\training_runs\stockless_xpu\best.nnue
isready
position startpos
go depth 8
quit
```

Only promote the model if the engine confirms NNUE load, no illegal moves,
passes `bench`/repeated loading, has acceptable NPS, and wins a paired
multi-opening test against **exactly the same STOCKLESS binary with the
original NNUE**. An attack bias alone cannot guarantee higher Elo.

## Limits and forward path

This first implementation changes **only the output layer**. Training
HalfKAv2_hm, Threats and PP features themselves requires a much larger
fully differentiable feature-transformer model and a safe exporter. Do not
mislabel the FC2 experiment as an end-to-end 10-million-position NNUE retrain.
All original Stockfish code remains GPLv3; preserve required notices and
licenses when redistributing the resulting engine.
