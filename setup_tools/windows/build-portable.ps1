<#
.SYNOPSIS
    Build the DDT4ALL UI portable Windows zip (PyInstaller onedir + Compress-Archive).

.DESCRIPTION
    Usage:   powershell -NoProfile -ExecutionPolicy Bypass -File setup_tools/windows/build-portable.ps1 VERSION
      VERSION   release version WITHOUT a leading "v", e.g. 3.1.3 or 3.1.3-dev.42.abc1234

    Can be run from any directory. Installs nothing: "python" (or $env:PYTHON) with
    the project dependencies and PyInstaller must already be on PATH, otherwise the
    script stops early. Works on Windows PowerShell 5.1 and PowerShell 7.

    Environment variables (all optional):
      PYTHON             Python interpreter to use                     (default: python)
      DDT4ALL_BUILD_DIR  scratch root; this script uses <dir>\windows-portable
                         and wipes only that sub-folder                 (default: <repo>\build)
      DDT4ALL_OUT_DIR    where the zip is written                      (default: <repo>\dist-packages)

    Output, in DDT4ALL_OUT_DIR:
      DDT4ALL-UI-<VERSION>-windows-x64-portable.zip
      containing one top-level folder DDT4ALL\ with DDT4ALL.exe (plus _internal\).
      The app stores ecu.zip / ecus\ / config.json / json\ / logs\ next to DDT4ALL-UI.exe
      (the launcher creates json\ on first run), so the unzipped folder must live
      somewhere writable.
#>
param(
    [Parameter(Mandatory = $true, Position = 0)]
    [string]$Version
)

$ErrorActionPreference = "Stop"

function Fail([string]$Message) {
    [Console]::Error.WriteLine("error: $Message")
    exit 1
}

if ($Version -match '^[vV]') { Fail "VERSION must not start with 'v' (got '$Version')" }
if ($Version -notmatch '^[0-9A-Za-z][0-9A-Za-z._+-]*$') { Fail "invalid VERSION '$Version'" }

$Root = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
$Spec = Join-Path $Root "setup_tools\pyinstaller\ddt4all.spec"

$BuildRoot = $env:DDT4ALL_BUILD_DIR
if ([string]::IsNullOrEmpty($BuildRoot)) { $BuildRoot = Join-Path $Root "build" }
$OutDir = $env:DDT4ALL_OUT_DIR
if ([string]::IsNullOrEmpty($OutDir)) { $OutDir = Join-Path $Root "dist-packages" }

$Python = $env:PYTHON
if ([string]::IsNullOrEmpty($Python)) { $Python = "python" }

# --- tool checks ------------------------------------------------------------
if (-not (Get-Command $Python -ErrorAction SilentlyContinue)) { Fail "'$Python' not found on PATH" }
if (-not (Test-Path -LiteralPath $Spec)) { Fail "missing $Spec" }
& $Python -m PyInstaller --version | Out-Null
if ($LASTEXITCODE -ne 0) { Fail "PyInstaller is not installed for '$Python' (pip install pyinstaller)" }

$Work = Join-Path $BuildRoot "windows-portable"
$PyiDist = Join-Path $Work "pyinstaller\dist"
$PyiWork = Join-Path $Work "pyinstaller\work"
$Zip = Join-Path $OutDir "DDT4ALL-UI-$Version-windows-x64-portable.zip"

if (Test-Path -LiteralPath $Work) { Remove-Item -LiteralPath $Work -Recurse -Force }
New-Item -ItemType Directory -Force -Path $PyiDist, $PyiWork, $OutDir | Out-Null

# --- 1. PyInstaller ---------------------------------------------------------
Write-Host "==> PyInstaller (version $Version)"
$env:DDT4ALL_VERSION = $Version
& $Python -m PyInstaller --noconfirm --clean --distpath $PyiDist --workpath $PyiWork $Spec
if ($LASTEXITCODE -ne 0) { Fail "PyInstaller failed with exit code $LASTEXITCODE" }

$AppDir = Join-Path $PyiDist "DDT4ALL-UI"
if (-not (Test-Path -LiteralPath (Join-Path $AppDir "DDT4ALL-UI.exe"))) {
    Fail "PyInstaller did not produce $AppDir\DDT4ALL.exe"
}

# --- 2. zip -----------------------------------------------------------------
Write-Host "==> Compress-Archive: $Zip"
if (Test-Path -LiteralPath $Zip) { Remove-Item -LiteralPath $Zip -Force }
# Passing the folder itself (not \*) keeps DDT4ALL\ as the top-level entry.
Compress-Archive -LiteralPath $AppDir -DestinationPath $Zip -CompressionLevel Optimal
if (-not (Test-Path -LiteralPath $Zip)) { Fail "zip was not created: $Zip" }

$SizeMb = [math]::Round((Get-Item -LiteralPath $Zip).Length / 1MB, 1)
Write-Host "Done: $Zip ($SizeMb MB)"
