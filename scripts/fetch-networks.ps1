$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $PSScriptRoot
$NetRoot = Join-Path $Root "networks"
$SfDir = Join-Path $NetRoot "stockfish"
$RkDir = Join-Path $NetRoot "reckless"

New-Item -ItemType Directory -Force -Path $SfDir, $RkDir | Out-Null

$SfName = "nn-134a887f4c8f.nnue"
$RkName = "v60-7f587dfb.nnue"

$SfPath = Join-Path $SfDir $SfName
$RkPath = Join-Path $RkDir $RkName

if (-not (Test-Path $SfPath)) {
    Write-Host "[Stockless] Downloading Stockfish NNUE..."
    try {
        Invoke-WebRequest -UseBasicParsing "https://tests.stockfishchess.org/api/nn/$SfName" -OutFile $SfPath
    } catch {
        Invoke-WebRequest -UseBasicParsing "https://raw.githubusercontent.com/official-stockfish/networks/master/$SfName" -OutFile $SfPath
    }
}

$hash = (Get-FileHash -Algorithm SHA256 $SfPath).Hash.ToLower()
if (-not $SfName.StartsWith("nn-" + $hash.Substring(0, 12))) {
    Remove-Item $SfPath -Force
    throw "Stockfish NNUE checksum does not match its content-addressed filename."
}

if (-not (Test-Path $RkPath)) {
    Write-Host "[Stockless] Downloading Reckless NNUE..."
    Invoke-WebRequest -UseBasicParsing "https://github.com/codedeliveryservice/RecklessNetworks/releases/download/networks/$RkName" -OutFile $RkPath
}

Write-Host "Stockfish NNUE: $SfPath"
Write-Host "Reckless NNUE:  $RkPath"
