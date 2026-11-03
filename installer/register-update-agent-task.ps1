#requires -Version 5.1
<##
.SYNOPSIS
    Programme l'agent hôte de mise à jour (appliquer-mise-a-jour-en-attente.ps1) chaque minute.
#>
[CmdletBinding()]
param(
    [switch]$Force,
    [string]$TaskName = 'YELEN SCHOOL - Agent de mise a jour'
)

$ErrorActionPreference = 'Stop'
$AgentScript = Join-Path $PSScriptRoot 'appliquer-mise-a-jour-en-attente.ps1'

if (-not (Get-Command Register-ScheduledTask -ErrorAction SilentlyContinue)) { exit 0 }
if (-not (Test-Path -LiteralPath $AgentScript)) { exit 0 }

$existante = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
if ($null -ne $existante) {
    if ($existante.State -eq 'Running') { exit 0 }
    if (-not $Force) { exit 0 }
}

$estAdmin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole(
    [Security.Principal.WindowsBuiltInRole]::Administrator
)
$userId = [System.Security.Principal.WindowsIdentity]::GetCurrent().Name
$arguments = "-NoProfile -NonInteractive -ExecutionPolicy Bypass -WindowStyle Hidden -File `"$AgentScript`""
$action = New-ScheduledTaskAction -Execute 'powershell.exe' -Argument $arguments
$trigger = New-ScheduledTaskTrigger -Once -At (Get-Date).AddMinutes(1) `
    -RepetitionInterval (New-TimeSpan -Minutes 1) -RepetitionDuration (New-TimeSpan -Days 3650)

if ($estAdmin) {
    $principal = New-ScheduledTaskPrincipal -UserId $userId -LogonType S4U -RunLevel Highest
} else {
    $principal = New-ScheduledTaskPrincipal -UserId $userId -LogonType Interactive -RunLevel Limited
}

$settings = New-ScheduledTaskSettingsSet -MultipleInstances IgnoreNew `
    -ExecutionTimeLimit (New-TimeSpan -Minutes 30) `
    -StartWhenAvailable -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries

Register-ScheduledTask `
    -TaskName $TaskName `
    -Action $action `
    -Trigger $trigger `
    -Principal $principal `
    -Settings $settings `
    -Description 'Applique les archives .zip déposées depuis Configuration > Mise à jour' `
    -Force | Out-Null
