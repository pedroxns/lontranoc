#requires -Version 5.1
<#
.SYNOPSIS
  Create three LontraZ 2.0 GitHub repositories without altering the originals.
.DESCRIPTION
  Run in PowerShell on the workstation with Git, GitHub CLI (gh), and SSH access.
  Default is read-only preflight. Add -Apply to create private repositories.
  Backend history is preserved: refactor/otterpilot becomes otterpilot/main.
  S3 and P4 receive documentation-only initial commits until their real firmware
  sources are located and imported. This script does not flash any hardware.
.EXAMPLE
  .\tools\split_lontraz_repos.ps1
  .\tools\split_lontraz_repos.ps1 -Apply
#>
[CmdletBinding()]
param(
    [switch] $Apply,
    [string] $Owner = "pedroxns",
    [string] $BaseBranch = "refactor/otterpilot"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Invoke-CommandChecked {
    param([string] $Command, [string[]] $Arguments)
    & $Command @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "$Command failed (exit $LASTEXITCODE): $($Arguments -join ' ')"
    }
}
function Assert-Command {
    param([string] $Name)
    if (-not (Get-Command $Name -ErrorAction SilentlyContinue)) {
        throw "Missing required command: $Name"
    }
}
Assert-Command "git"
Assert-Command "gh"
Invoke-CommandChecked "gh" @("auth", "status")
$desired = @("otterpilot", "lontraz-display-s3", "lontraz-core-p4")
$existingJson = (& gh repo list $Owner --limit 1000 --json name | Out-String)
if ($LASTEXITCODE -ne 0) { throw "Could not list existing repositories of $Owner" }
$names = @((ConvertFrom-Json $existingJson) | ForEach-Object { $_.name })
foreach ($name in $desired) {
    if ($names -contains $name) {
        throw "$Owner/$name already exists: aborting to avoid any overwrite. Inspect it manually."
    }
}
Write-Host "Preflight OK. No existing destination repositories."
Write-Host "Plan: create PRIVATE repositories $($desired -join ', ')."
Write-Host "Source: $Owner/lontranoc, branch $BaseBranch, preserved Git ancestry."
Write-Host "S3/P4 repos will have README only, not replacement firmware."
if (-not $Apply) {
    Write-Host "Dry-run only. Re-run with -Apply to execute."
    exit 0
}
$work = Join-Path ([IO.Path]::GetTempPath()) ("lontraz-v2-split-" + [guid]::NewGuid().ToString("N"))
New-Item -ItemType Directory -Path $work | Out-Null
Write-Host "Temporary workdir: $work (retained for auditing)."

# Backend: clone the actual advanced branch; do not use stale main.
$backendPath = Join-Path $work "otterpilot"
Invoke-CommandChecked "git" @("clone", "--single-branch", "--branch", $BaseBranch,
    "https://github.com/$Owner/lontranoc.git", $backendPath)
$sourceSha = (& git -C $backendPath rev-parse HEAD).Trim()
if ($LASTEXITCODE -ne 0) { throw "Could not read backend source commit." }
# The historical code can contain old secrets: inspect tracked files first.
$tracked = & git -C $backendPath ls-files
if ($LASTEXITCODE -ne 0) { throw "Could not inventory backend tracked files." }
$forbidden = @($tracked | Where-Object {
    ($_ -match '(^|/)\.env($|\.)') -or ($_ -match '(^|/)(sdkconfig|secrets\.yaml|credentials?\.json)$') -or
    ($_ -match '\.(pem|p12|pfx|key)$')
})
if ($forbidden.Count -gt 0) {
    Write-Host "Potential secrets found. ABORT before publishing:" -ForegroundColor Yellow
    $forbidden | ForEach-Object { Write-Host "  $_" }
    throw "Review tracked files and Git history manually before migration."
}
Write-Host "Backend SHA: $sourceSha"
Write-Host "NOTE: automated filename checks cannot rule out secrets in file content or history."

Invoke-CommandChecked "gh" @("repo", "create", "$Owner/otterpilot", "--private",
    "--description", "OtterPilot: observability and local AI copilot for homelabs")
Invoke-CommandChecked "git" @("-C", $backendPath, "remote", "add", "migration-target",
    "git@github.com:$Owner/otterpilot.git")
Invoke-CommandChecked "git" @("-C", $backendPath, "push", "-u", "migration-target", "HEAD:refs/heads/main")
Write-Host "Created $Owner/otterpilot main at $sourceSha"

function New-DocumentationOnlyRepo {
    param([string] $Name, [string] $Description, [string] $Readme, [string] $ProtocolReadme)
    $path = Join-Path $work $Name
    New-Item -ItemType Directory -Path $path | Out-Null
    Set-Content -Path (Join-Path $path "README.md") -Value $Readme -Encoding UTF8
    if ($ProtocolReadme) {
        New-Item -ItemType Directory -Path (Join-Path $path "protocol") | Out-Null
        Set-Content -Path (Join-Path $path "protocol\README.md") -Value $ProtocolReadme -Encoding UTF8
    }
    Invoke-CommandChecked "git" @("-C", $path, "init", "-b", "main")
    Invoke-CommandChecked "git" @("-C", $path, "add", ".")
    Invoke-CommandChecked "git" @("-C", $path, "commit", "-m", "docs: establish device repository without replacing firmware")
    Invoke-CommandChecked "gh" @("repo", "create", "$Owner/$Name", "--private", "--description", $Description)
    Invoke-CommandChecked "git" @("-C", $path, "remote", "add", "origin",
        "git@github.com:$Owner/$Name.git")
    Invoke-CommandChecked "git" @("-C", $path, "push", "-u", "origin", "main")
    Write-Host "Created $Owner/$Name (documentation only)"
}

$s3Readme = @'
# LontraZ Display — ESP32-S3 AMOLED

Hardware: Waveshare ESP32-S3-Touch-AMOLED-1.75 (non-G), 466x466 CO5300/QSPI,
touch CST9217, IMU QMI8658, ES7210 microphones, ES8311 audio codec.

Responsibilities: avatar and animations, touch/IMU events, continuous I2S/DMA
capture of two microphones, telemetry, UART client to ESP32-P4.

**IMPORTANT:** This repository contains NO firmware yet.
Locate and import the original working S3 firmware from the workstation
preserving its actual source and history when possible. Do not flash a scaffold.
See migration plan in pedroxns/lontranoc:
docs/LONTRAZ_V2_REPOSITORIES.md on branch chore/lontraz-v2-repository-split.
'@
$p4Readme = @'
# LontraZ Core — Guition ESP32-P4 + ESP32-C6

Initial hardware: Guition JC-ESP32P4-M3-DEV (P4 + C6).
Responsibilities: UART/audio receiver, buffering, WakeNet/VAD/AFE,
connectivity with OtterPilot, dialogue state, OTA and telemetry.

**IMPORTANT:** Documentation-only repository; firmware not implemented yet.
The separate pedroxns/tela-esp32p4---rack project is a prior rack monitor:
reference its BSP/pinout only; DO NOT replace or reflash that project as LontraZ.

A hardware engineer must confirm the Guition's physical GPIO pinout against
schematics before wiring TX/RX. Never connect two USB-powered boards through
5 V or 3.3 V rails.
'@
$protocolReadme = @'
# LontraZ UART interface: proposal, not implemented

Use 3.3 V UART, TX→RX crossed and common GND. Versioned framing,
CRC, sequence numbers, heartbeat, buffer-overflow counters and priority
for control messages. No raw framebuffer over UART.

First pass: HELLO, HEARTBEAT, SET_AVATAR_STATE, TOUCH_EVENT, IMU_EVENT,
AUDIO_START, AUDIO_FRAME, AUDIO_STOP, STATUS.

Two PCM mic channels at 16 kHz, signed 16-bit: 64 kB/s payload minimum.
921600 baud UART 8N1: ≈92 kB/s theoretical before protocol overhead;
validate ≥2 Mbaud and fallback using measurements. Do not guess pins.
'@
New-DocumentationOnlyRepo "lontraz-display-s3" "LontraZ ESP32-S3 AMOLED display and microphone capture" $s3Readme ""
New-DocumentationOnlyRepo "lontraz-core-p4" "LontraZ ESP32-P4 core and voice processing" $p4Readme $protocolReadme
Write-Host "Repository separation complete. Remaining: import real S3 firmware and implement integration."
Write-Host "Do not delete or rename source repositories."
