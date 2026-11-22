# Native command failure regressions, without a compiler or Pester dependency.
$ErrorActionPreference = "Stop"
$PSNativeCommandUseErrorActionPreference = $false
if ($env:OS -ne "Windows_NT") { throw "This regression runs on Windows." }

$Repository = Split-Path -Parent $PSScriptRoot
$Fixture = Join-Path ([System.IO.Path]::GetTempPath()) ("stockless windows test " + [guid]::NewGuid())
$EnvironmentNames = @("PATH", "STOCKLESS_ARCH", "STOCKLESS_PGO", "STOCKLESS_JOBS",
    "STOCKLESS_TEST_CALLS", "STOCKLESS_TEST_BINARY", "STOCKLESS_TEST_GIT_CODE",
    "STOCKLESS_TEST_PYTHON_CODE", "STOCKLESS_TEST_MAKE_CODE", "STOCKLESS_TEST_NO_BINARY")
$SavedEnvironment = @{}
foreach ($Name in $EnvironmentNames) {
    $SavedEnvironment[$Name] = [Environment]::GetEnvironmentVariable($Name, "Process")
}
$OriginalLocation = (Get-Location).Path

try {
    foreach ($Directory in @("scripts", "src/stockless", "fake-bin", "build/stockless-src/src")) {
        New-Item -ItemType Directory -Force (Join-Path $Fixture $Directory) | Out-Null
    }
    Copy-Item (Join-Path $Repository "scripts/build-windows.ps1") (Join-Path $Fixture "scripts/")
    Copy-Item (Join-Path $Repository "src/stockless/config.h") (Join-Path $Fixture "src/stockless/")
    $FakeBin = Join-Path $Fixture "fake-bin"
    @'
@echo off
echo git>>"%STOCKLESS_TEST_CALLS%"
exit /b %STOCKLESS_TEST_GIT_CODE%
'@ | Set-Content (Join-Path $FakeBin "git.cmd") -Encoding ascii
    @'
@echo off
echo python>>"%STOCKLESS_TEST_CALLS%"
exit /b %STOCKLESS_TEST_PYTHON_CODE%
'@ | Set-Content (Join-Path $FakeBin "python.cmd") -Encoding ascii
    # Put redirection before echo: bash's final jobs argument is numeric, so
    # appending >> after %* would turn its trailing "2" into stderr redirection.
    @'
@echo off
>>"%STOCKLESS_TEST_CALLS%" echo make %*
if not "%STOCKLESS_TEST_MAKE_CODE%"=="0" exit /b %STOCKLESS_TEST_MAKE_CODE%
if "%STOCKLESS_TEST_NO_BINARY%"=="1" exit /b 0
echo built fixture>"%STOCKLESS_TEST_BINARY%"
exit /b 0
'@ | Set-Content (Join-Path $FakeBin "make.cmd") -Encoding ascii
    @'
@echo off
>>"%STOCKLESS_TEST_CALLS%" echo bash %*
exit /b %STOCKLESS_TEST_MAKE_CODE%
'@ | Set-Content (Join-Path $FakeBin "bash.cmd") -Encoding ascii

    $env:PATH = "$FakeBin;$env:PATH"
    $env:STOCKLESS_ARCH = "x86-64-avx2"
    $env:STOCKLESS_JOBS = "2"
    $env:STOCKLESS_TEST_CALLS = Join-Path $Fixture "calls.txt"
    $env:STOCKLESS_TEST_BINARY = Join-Path $Fixture "build/stockless-src/src/stockless.exe"

    function Invoke-BuildCase {
        param([string]$Name, [int]$GitCode, [int]$PythonCode, [int]$MakeCode,
              [string]$ExpectedCalls, [string]$ExpectedError = "",
              [string]$Pgo = "0", [bool]$NoBinary = $false)
        $env:STOCKLESS_TEST_GIT_CODE = "$GitCode"
        $env:STOCKLESS_TEST_PYTHON_CODE = "$PythonCode"
        $env:STOCKLESS_TEST_MAKE_CODE = "$MakeCode"
        $env:STOCKLESS_PGO = $Pgo
        $env:STOCKLESS_TEST_NO_BINARY = if ($NoBinary) { "1" } else { "0" }
        Remove-Item $env:STOCKLESS_TEST_CALLS -ErrorAction SilentlyContinue
        if ($NoBinary) {
            Remove-Item $env:STOCKLESS_TEST_BINARY -ErrorAction SilentlyContinue
        } else {
            "stale build fixture" | Set-Content $env:STOCKLESS_TEST_BINARY
        }
        $Failure = ""
        try {
            & (Join-Path $Fixture "scripts/build-windows.ps1") 6>&1 | Out-Null
        } catch {
            $Failure = $_.Exception.Message
        }
        if ($ExpectedError -and $Failure -notlike "*$ExpectedError*") {
            throw "${Name}: expected '$ExpectedError', got '$Failure'"
        }
        if (-not $ExpectedError -and $Failure) { throw "${Name}: unexpected failure: $Failure" }
        $Calls = @(Get-Content $env:STOCKLESS_TEST_CALLS -ErrorAction SilentlyContinue)
        $Names = ($Calls | ForEach-Object { ($_ -split " ")[0] }) -join ","
        if ($Names -ne $ExpectedCalls) { throw "${Name}: commands were '$Names', expected '$ExpectedCalls'" }
        if ((Get-Location).Path -ne $OriginalLocation) { throw "${Name}: caller working directory changed" }
        if ($Name -eq "successful build" -and ($Calls[-1] -notmatch "COMP=mingw")) {
            throw "The Windows build did not request the MinGW compiler profile"
        }
        if ($Pgo -eq "1" -and $Calls[-1] -notmatch ' mingw "?2"?\s*$') {
            throw "The PGO helper arguments were not preserved, including the trailing jobs count"
        }
        Write-Host "PASS: $Name"
    }

    Invoke-BuildCase "failed git" 17 0 0 "git" "submodule initialization failed with 17"
    Invoke-BuildCase "failed materialization with stale build" 0 18 0 "git,python" "materialization failed with 18"
    Invoke-BuildCase "failed make" 0 0 19 "git,python,make" "make build failed with 19"
    Invoke-BuildCase "failed PGO helper" 0 0 20 "git,python,bash" "make profile-build failed with 20" -Pgo "1"
    Invoke-BuildCase "missing output" 0 0 0 "git,python,make" "did not produce" -NoBinary $true
    Invoke-BuildCase "invalid PGO option" 0 0 0 "" "STOCKLESS_PGO must be 0 or 1" -Pgo "2"
    Invoke-BuildCase "successful build" 0 0 0 "git,python,make"
} finally {
    foreach ($Name in $EnvironmentNames) {
        [Environment]::SetEnvironmentVariable($Name, $SavedEnvironment[$Name], "Process")
    }
    Set-Location $OriginalLocation
    Remove-Item -LiteralPath $Fixture -Recurse -Force -ErrorAction SilentlyContinue
}
