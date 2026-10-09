#requires -Version 5.1
<##
.SYNOPSIS
    Programme le démarrage automatique de YELEN SCHOOL à l'ouverture de session Windows.
#>

[CmdletBinding()]
param(
    [string]$TaskName = 'YELEN SCHOOL - Démarrage automatique'
)

$ErrorActionPreference = 'Stop'
$Root = [System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))
$StartScript = Join-Path $PSScriptRoot 'start-local.ps1'
$LogDirectory = Join-Path $Root 'logs'

if (-not (Get-Command Register-ScheduledTask -ErrorAction SilentlyContinue)) {
    throw 'Le module ScheduledTasks est indisponible sur cette version de Windows.'
}
if (-not (Test-Path $StartScript)) {
    throw "Script introuvable : $StartScript"
}

New-Item -ItemType Directory -Path $LogDirectory -Force | Out-Null
$userId = [System.Security.Principal.WindowsIdentity]::GetCurrent().Name
$arguments = "-NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File `"$StartScript`""
$action = New-ScheduledTaskAction -Execute 'powershell.exe' -Argument $arguments
$trigger = New-ScheduledTaskTrigger -AtLogOn -User $userId
$principal = New-ScheduledTaskPrincipal -UserId $userId -LogonType InteractiveToken -RunLevel Highest

Register-ScheduledTask `
    -TaskName $TaskName `
    -Action $action `
    -Trigger $trigger `
    -Principal $principal `
    -Description 'Démarre automatiquement Docker et YELEN SCHOOL à l’ouverture de session' `
    -Force | Out-Null

Write-Host '[OK] Démarrage automatique programmé.' -ForegroundColor Green
Write-Host "Tâche : $TaskName"
Write-Host 'La tâche s’exécutera à la prochaine ouverture de session Windows.'
Write-Host "Journal : $LogDirectory\startup.log"
