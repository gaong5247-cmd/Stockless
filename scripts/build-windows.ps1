$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $PSScriptRoot
# Keep the distributed default AVX2 target; set STOCKLESS_ARCH=native only
# for binaries intended for the machine performing the compilation.
$Arch = if ($env:STOCKLESS_ARCH) { $env:STOCKLESS_ARCH } else { "x86-64-avx2" }
$Pgo = if ($env:STOCKLESS_PGO) { $env:STOCKLESS_PGO } else { "0" }
if ($Pgo -notin @("0", "1")) { throw "STOCKLESS_PGO must be 0 or 1" }
$Target = if ($Pgo -eq "1") { "profile-build" } else { "build" }
$Jobs = if ($env:STOCKLESS_JOBS) { [int]$env:STOCKLESS_JOBS } else { 2 }
if ($Jobs -lt 1) { throw "STOCKLESS_JOBS must be positive" }

Push-Location $Root
try {
    Write-Host "[Stockless] Initializing pinned upstream engines..."
    git submodule update --init --recursive
    # ErrorActionPreference does not reliably turn native exit codes into
    # terminating errors, especially in Windows PowerShell 5.1.
    if ($LASTEXITCODE -ne 0) { throw "Stockless submodule initialization failed with $LASTEXITCODE" }

    Write-Host "[Stockless] Materializing hybrid Stockfish tree..."
    python tools/materialize.py
    if ($LASTEXITCODE -ne 0) { throw "Stockless materialization failed with $LASTEXITCODE" }

    $EngineSrc = Join-Path $Root "build/stockless-src/src"
    Write-Host "[Stockless] Building ARCH=$Arch TARGET=$Target JOBS=$Jobs ..."
    if ($Pgo -eq "1") {
        bash (Join-Path $Root "scripts/build-pgo.sh") $EngineSrc $Arch "mingw" $Jobs
    } else {
        make -C $EngineSrc "-j$Jobs" $Target "ARCH=$Arch" "COMP=mingw"
    }
    if ($LASTEXITCODE -ne 0) { throw "Stockless make $Target failed with $LASTEXITCODE" }

    $Binary = Join-Path $EngineSrc "stockless.exe"
    if (-not (Test-Path -LiteralPath $Binary -PathType Leaf)) { throw "Stockless build did not produce $Binary" }
    $Config = Get-Content (Join-Path $Root "src/stockless/config.h") -Raw
    if ($Config -notmatch 'Version = "([^"]+)"') { throw "Missing engine version" }
    Write-Host ""
    Write-Host "Build complete."
    Write-Host "Binary: $Binary"
    Write-Host "UCI identity: Stockless $($Matches[1])"
    Write-Host "Hybrid search is ON by default; Overdrive is OFF."
    Write-Host "Enable in UCI with: setoption name StocklessHybrid value true"
    Write-Host "Aggression default: 145 (range 0..200)"
    Write-Host "PGO: $Target (set STOCKLESS_PGO=1 to use the verified PGO helper)"
    Write-Host "ARCH=native creates a CPU-specific binary; AVX2 also requires an AVX2-capable CPU."
} finally {
    Pop-Location
}
