# Blender Sync - Package Script (Windows PowerShell)
# Builds a .zip file ready for upload to extensions.blender.org
#
# Prerequisites:
#   1. Blender 5.0+ installed (add to PATH or set $BLENDER_EXE)
#   2. Run from the project root directory
#
# Usage:
#   .\scripts\package.ps1
#   .\scripts\package.ps1 -BlenderExe "F:\SteamLibrary\steamapps\common\Blender\blender.exe"
#
# Output:
#   blender_sync-0.1.0.zip

param(
    [string]$BlenderExe = "blender",
    [string]$OutputDir = "dist"
)

$ErrorActionPreference = "Stop"

# Determine project root (parent of scripts/)
$ProjectRoot = Split-Path -Parent $PSScriptRoot

# Ensure dist dir exists
$distDir = Join-Path $ProjectRoot $OutputDir
New-Item -ItemType Directory -Force -Path $distDir | Out-Null

# ── Version ──────────────────────────────────────────────
Write-Host "=== Blender Sync Packager ===" -ForegroundColor Cyan

# Check Blender
try {
    $blenderVersion = & $BlenderExe --version 2>&1 | Select-Object -First 1
    Write-Host "Blender: $blenderVersion"
} catch {
    Write-Host "ERROR: Cannot run blender. Set -BlenderExe to your blender executable." -ForegroundColor Red
    Write-Host "  Example: .\scripts\package.ps1 -BlenderExe 'C:\Program Files\Blender\blender.exe'"
    exit 1
}

# ── Validate manifest ────────────────────────────────────
Write-Host "Validating manifest..." -ForegroundColor Yellow
Push-Location (Join-Path $ProjectRoot "blender_sync")
try {
    $null = & $BlenderExe --command extension validate 2>&1
    Write-Host "  Manifest OK" -ForegroundColor Green
} catch {
    # Validate prints validation output, check for errors
    $output = & $BlenderExe --command extension validate 2>&1
    if ($LASTEXITCODE -ne 0) {
        Write-Host "  Manifest validation failed:" -ForegroundColor Red
        Write-Host $output
        Pop-Location
        exit 1
    }
} finally {
    Pop-Location
}

# ── Build extension zip ──────────────────────────────────
Write-Host "Building extension package..." -ForegroundColor Yellow
Push-Location (Join-Path $ProjectRoot "blender_sync")
try {
    $buildOutput = & $BlenderExe --command extension build --output-dir $distDir 2>&1
    # Blender outputs to stderr even on success; check for "complete" in output
    if ($buildOutput -match "complete") {
        Write-Host "  Build OK" -ForegroundColor Green
    } else {
        Write-Host "ERROR: Build may have failed" -ForegroundColor Red
        Write-Host $buildOutput
    }
} finally {
    Pop-Location
}

# ── Find output ──────────────────────────────────────────
$zipFile = Get-ChildItem $distDir -Filter "*.zip" | Sort-Object LastWriteTime -Descending | Select-Object -First 1

if (-not $zipFile) {
    Write-Host "ERROR: No .zip produced in $distDir" -ForegroundColor Red
    exit 1
}

$sizeMB = [math]::Round($zipFile.Length / 1MB, 2)
Write-Host ""
Write-Host "=== Package Ready ===" -ForegroundColor Green
Write-Host "  File: $($zipFile.FullName)"
Write-Host "  Size: $sizeMB MB"
Write-Host ""
Write-Host "Next steps:"
Write-Host "  1. Test: Install from Disk in Blender (Edit > Preferences > Get Extensions)"
Write-Host "  2. Upload: https://extensions.blender.org/submit/"
Write-Host "  3. Check: https://extensions.blender.org/approval-queue/"
Write-Host ""
Write-Host "To publish updates automatically via CI/CD, see:"
Write-Host "  https://developer.blender.org/docs/features/extensions/ci_cd/"
