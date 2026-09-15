#requires -Version 5.1
<##
.SYNOPSIS
    Programme l'envoi quotidien des SMS automatiques sous Windows.
#>

[CmdletBinding()]
param(
    [ValidatePattern('^([01][0-9]|2[0-3]):[0-5][0-9]$')]
    [string]$Time = '07:00',
    [string]$TaskName = 'YELEN SCHOOL - SMS automatiques'
)

$ErrorActionPreference = 'Stop'
$Root = [System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))
$SmsScript = Join-Path $PSScriptRoot 'run-sms-auto.ps1'
$LogDirectory = Join-Path $Root 'logs'
$LogFile = Join-Path $LogDirectory 'sms-auto.log'

if (-not (Get-Command Register-ScheduledTask -ErrorAction SilentlyContinue)) {
    throw 'Le module ScheduledTasks est indisponible sur cette version de Windows.'
}
if (-not (Test-Path $SmsScript)) {
    throw "Script introuvable : $SmsScript"
}

New-Item -ItemType Directory -Path $LogDirectory -Force | Out-Null
$userId = [System.Security.Principal.WindowsIdentity]::GetCurrent().Name
$arguments = "-NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File `"$SmsScript`" -TaskLog `"$LogFile`""
$action = New-ScheduledTaskAction -Execute 'powershell.exe' -Argument $arguments
$trigger = New-ScheduledTaskTrigger -Daily -At ([datetime]::ParseExact($Time, 'HH:mm', $null))
$principal = New-ScheduledTaskPrincipal -UserId $userId -LogonType InteractiveToken -RunLevel Highest

Register-ScheduledTask `
    -TaskName $TaskName `
    -Action $action `
    -Trigger $trigger `
    -Principal $principal `
    -Description 'Exécute les déclencheurs SMS automatiques YELEN SCHOOL' `
    -Force | Out-Null

Write-Host "[OK] SMS automatiques programmés à $Time." -ForegroundColor Green
Write-Host "Tâche : $TaskName"
Write-Host 'Testez-la depuis le Planificateur de tâches avec « Exécuter ».'
Write-Host "Journal : $LogFile"
