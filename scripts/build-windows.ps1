$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

Write-Host "[Stockless] Initializing pinned upstream engines..."
git submodule update --init --recursive

Write-Host "[Stockless] Materializing hybrid Stockfish tree..."
python tools/materialize.py

$EngineSrc = Join-Path $Root "build/stockless-src/src"
Set-Location $EngineSrc

# Keep the distributed default AVX2 target; set STOCKLESS_ARCH=native only
# for binaries intended for the machine performing the compilation.
$Arch = if ($env:STOCKLESS_ARCH) { $env:STOCKLESS_ARCH } else { "x86-64-avx2" }
$Target = if ($env:STOCKLESS_PGO -eq "1") { "profile-build" } else { "build" }
$Jobs = if ($env:STOCKLESS_JOBS) { [int]$env:STOCKLESS_JOBS } else { 2 }
if ($Jobs -lt 1) { throw "STOCKLESS_JOBS must be positive" }

Write-Host "[Stockless] Building ARCH=$Arch TARGET=$Target JOBS=$Jobs ..."
make "-j$Jobs" $Target "ARCH=$Arch"
if ($LASTEXITCODE -ne 0) { throw "Stockless make $Target failed with $LASTEXITCODE" }

Write-Host ""
Write-Host "Build complete."
Write-Host "Binary is under: $EngineSrc"
Write-Host "UCI identity: Stockless v0.7.1"
Write-Host "Hybrid search is ON by default; Overdrive and ThreatHistory are OFF."
Write-Host "Enable in UCI with: setoption name StocklessHybrid value true"
Write-Host "Aggression default: 145 (range 0..200)"
Write-Host "PGO: $Target (set STOCKLESS_PGO=1 to use the pinned Stockfish profile-build)"
Write-Host "ARCH=native creates a CPU-specific binary; keep AVX2 for broad compatibility."
Write-Host "ThreatHistory: default OFF (toggle with StocklessThreatHistory)"
