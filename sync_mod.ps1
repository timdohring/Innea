<#
.SYNOPSIS
    Mirror the repo's mod folder into the live EU5 mod directory.

.DESCRIPTION
    Copies `wip mod folder\` over the installed mod using robocopy /MIR, so the install
    becomes an exact mirror of the repo — including DELETIONS, which a plain copy misses.

    That gap has bitten before: deleting a stale vanilla override in the repo while the
    install kept its copy left two files defining the same topographies, and the engine
    silently used the stale one.

.PARAMETER DryRun
    List what would change without touching anything.

.PARAMETER Force
    Sync even if eu5.exe is running. Off by default — the game reads these files at
    startup and mirroring under a live process can half-apply a change.

.EXAMPLE
    .\sync_mod.ps1
    .\sync_mod.ps1 -DryRun
#>
[CmdletBinding()]
param(
    [switch]$DryRun,
    [switch]$Force
)

$ErrorActionPreference = 'Stop'

$Source = Join-Path $PSScriptRoot 'wip mod folder'
$Target = 'C:\Program Files (x86)\Steam\steamapps\common\Europa Universalis V\game\mod\test_modding'

# --- sanity checks -------------------------------------------------------
if (-not (Test-Path -LiteralPath $Source)) {
    throw "Source not found: $Source"
}
# Refuse to mirror something that isn't a mod - /MIR deletes, so a wrong source is costly.
$metadata = Join-Path $Source '.metadata\metadata.json'
if (-not (Test-Path -LiteralPath $metadata)) {
    throw "Source has no .metadata\metadata.json - refusing to mirror: $Source"
}
if (-not (Test-Path -LiteralPath $Target)) {
    Write-Host "Target does not exist, it will be created: $Target" -ForegroundColor Yellow
}

$running = Get-Process -Name 'eu5' -ErrorAction SilentlyContinue
if ($running -and -not $Force -and -not $DryRun) {
    throw "eu5.exe is running (PID $($running.Id -join ', ')). Close the game, or pass -Force."
}

# --- mirror --------------------------------------------------------------
$flags = @('/MIR', '/NJH', '/NJS', '/NDL', '/NP', '/R:2', '/W:2')
if ($DryRun) { $flags += '/L' }

Write-Host ''
Write-Host "  from : $Source"
Write-Host "  to   : $Target"
Write-Host ("  mode : {0}" -f $(if ($DryRun) { 'DRY RUN - nothing will change' } else { 'MIRROR' }))
Write-Host ''

& robocopy $Source $Target @flags
$code = $LASTEXITCODE

# robocopy: 0-7 are success (bit 0 = copied, bit 1 = extras removed, bit 2 = mismatches),
# 8 and above are genuine failures.
if ($code -ge 8) {
    throw "robocopy failed with exit code $code"
}

$what = @()
if ($code -band 1) { $what += 'files copied' }
if ($code -band 2) { $what += 'extra files removed' }
if ($code -band 4) { $what += 'mismatched items' }
if (-not $what)    { $what += 'already identical' }

Write-Host ''
if ($DryRun) {
    Write-Host ("Dry run complete - would have: {0}" -f ($what -join ', ')) -ForegroundColor Cyan
} else {
    Write-Host ("Sync complete - {0}." -f ($what -join ', ')) -ForegroundColor Green
}

# robocopy's success codes (1/2/3) would otherwise surface as a failed exit status.
exit 0
