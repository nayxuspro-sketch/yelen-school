#requires -Version 5.1
<##
.SYNOPSIS
    Programme la surveillance de YELEN SCHOOL toutes les 5 minutes (surveiller-yelen.ps1).
#>
[CmdletBinding()]
param(
    [ValidateRange(1, 60)]
    [int]$Minutes = 5,
    [string]$TaskName = 'YELEN SCHOOL - Surveillance et alerte SMS'
)

$ErrorActionPreference = 'Stop'
$Root = [System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))
$WatchScript = Join-Path $PSScriptRoot 'surveiller-yelen.ps1'
$LogDirectory = Join-Path $Root 'logs'

if (-not (Get-Command Register-ScheduledTask -ErrorAction SilentlyContinue)) {
    throw 'Le module ScheduledTasks est indisponible sur cette version de Windows.'
}
if (-not (Test-Path $WatchScript)) {
    throw "Script introuvable : $WatchScript"
}
New-Item -ItemType Directory -Path $LogDirectory -Force | Out-Null

$arguments = "-NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File `"$WatchScript`""
$action = New-ScheduledTaskAction -Execute 'powershell.exe' -Argument $arguments
# Toutes les N minutes, dès l'ouverture de session (Docker Desktop vit dans la session utilisateur).
$userId = [System.Security.Principal.WindowsIdentity]::GetCurrent().Name
$trigger = New-ScheduledTaskTrigger -Once -At (Get-Date).AddMinutes(1) `
    -RepetitionInterval (New-TimeSpan -Minutes $Minutes) -RepetitionDuration (New-TimeSpan -Days 3650)
$principal = New-ScheduledTaskPrincipal -UserId $userId -LogonType Interactive -RunLevel Highest
$settings = New-ScheduledTaskSettingsSet -MultipleInstances IgnoreNew -ExecutionTimeLimit (New-TimeSpan -Minutes 10) `
    -StartWhenAvailable -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries

Register-ScheduledTask `
    -TaskName $TaskName `
    -Action $action `
    -Trigger $trigger `
    -Principal $principal `
    -Settings $settings `
    -Description 'Vérifie /health/ toutes les 5 minutes, relance les services et alerte par SMS' `
    -Force | Out-Null

Write-Host "[OK] Surveillance programmée toutes les $Minutes minutes." -ForegroundColor Green
Write-Host "Tâche : $TaskName"
Write-Host "Journal : $LogDirectory\surveillance.log"
Write-Host 'Dans .env : ALERTE_SMS_NUMEROS=+22670000000,+22676000000 (et SMS_HTTP_URL / SMS_HTTP_USER / SMS_HTTP_PASSWORD).'
