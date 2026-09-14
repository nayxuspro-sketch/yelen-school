#requires -Version 5.1
<##
.SYNOPSIS
    Programme une sauvegarde quotidienne de YELEN SCHOOL sous Windows.
#>

[CmdletBinding()]
param(
    [ValidatePattern('^([01][0-9]|2[0-3]):[0-5][0-9]$')]
    [string]$Time = '22:00',
    [string]$TaskName = 'YELEN SCHOOL - Sauvegarde PostgreSQL et médias'
)

$ErrorActionPreference = 'Stop'
$Root = [System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))
$BackupScript = Join-Path $PSScriptRoot 'backup-windows.ps1'
$BackupDirectory = Join-Path $Root 'backups'
$LogFile = Join-Path $BackupDirectory 'backup.log'

if (-not (Get-Command Register-ScheduledTask -ErrorAction SilentlyContinue)) {
    throw 'Le module ScheduledTasks est indisponible sur cette version de Windows.'
}
if (-not (Test-Path $BackupScript)) {
    throw "Script introuvable : $BackupScript"
}

New-Item -ItemType Directory -Path $BackupDirectory -Force | Out-Null
$arguments = "-NoProfile -ExecutionPolicy Bypass -File `"$BackupScript`" -OutputDirectory `"$BackupDirectory`" *> `"$LogFile`""
$action = New-ScheduledTaskAction -Execute 'powershell.exe' -Argument $arguments
$trigger = New-ScheduledTaskTrigger -Daily -At ([datetime]::ParseExact($Time, 'HH:mm', $null))
# Docker Desktop est généralement disponible dans la session de l'utilisateur
# connecté, pas dans une session système sans profil Docker.
$userId = [System.Security.Principal.WindowsIdentity]::GetCurrent().Name
$principal = New-ScheduledTaskPrincipal -UserId $userId -LogonType InteractiveToken -RunLevel Highest

Register-ScheduledTask `
    -TaskName $TaskName `
    -Action $action `
    -Trigger $trigger `
    -Principal $principal `
    -Description 'Sauvegarde quotidienne de la base et des médias YELEN SCHOOL' `
    -Force | Out-Null

Write-Host "[OK] Sauvegarde quotidienne programmée à $Time."
Write-Host "Tâche : $TaskName"
Write-Host 'Testez-la depuis le Planificateur de tâches avec « Exécuter ».'
