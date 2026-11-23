# Compile a Stockless native-feature probe WITHOUT modifying pinned submodules.
# Intentionally does not call scripts/build-windows.ps1, which re-materializes and
# would erase our local training instrumentation.
$ErrorActionPreference = "Stop"
$Root = (Resolve-Path (Join-Path $PSScriptRoot "../..")).Path
Push-Location $Root
try {
    git submodule update --init --recursive
    if ($LASTEXITCODE -ne 0) { throw "Submodule checkout failed" }
    python tools/materialize.py
    if ($LASTEXITCODE -ne 0) { throw "Materialization failed" }
    python tools/xpu_nnue/patch_probe.py
    if ($LASTEXITCODE -ne 0) { throw "Probe patch failed" }
    Push-Location (Join-Path $Root "build/stockless-src/src")
    try {
        $Arch = if ($env:STOCKLESS_ARCH) { $env:STOCKLESS_ARCH } else { "x86-64-avx2" }
        $Jobs = if ($env:STOCKLESS_JOBS) { [int]$env:STOCKLESS_JOBS } else { 2 }
        make "-j$Jobs" build "ARCH=$Arch"
        if ($LASTEXITCODE -ne 0) { throw "Probe engine build failed" }
    } finally { Pop-Location }
    Write-Host "Stockless training probe compiled; run UCI command 'stockless_features' to inspect"
} finally { Pop-Location }
