$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

Write-Host "[Stockless] Initializing pinned upstream engines..."
git submodule update --init --recursive

Write-Host "[Stockless] Materializing hybrid Stockfish tree..."
python tools/materialize.py

$EngineSrc = Join-Path $Root "build/stockless-src/src"
Set-Location $EngineSrc

$Arch = if ($env:STOCKLESS_ARCH) { $env:STOCKLESS_ARCH } else { "x86-64-avx2" }

Write-Host "[Stockless] Building ARCH=$Arch ..."
make -j build ARCH=$Arch

Write-Host ""
Write-Host "Build complete."
Write-Host "Binary is under: $EngineSrc"
Write-Host "UCI identity: Stockless v0.7"
Write-Host "Hybrid search is ON by default; Overdrive and ThreatHistory are OFF."
Write-Host "Enable in UCI with: setoption name StocklessHybrid value true"
Write-Host "Aggression default: 145 (range 0..200)"
Write-Host "ThreatHistory: default OFF (toggle with StocklessThreatHistory)"
