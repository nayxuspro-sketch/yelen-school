#requires -Version 5.1
<##
.SYNOPSIS
    Programme une restauration unique PostgreSQL et médias de YELEN SCHOOL.

.DESCRIPTION
    Une restauration remplace les données actuelles. Le paramètre
    -ConfirmRestore est obligatoire pour empêcher une programmation accidentelle.
    La tâche est exécutée une seule fois au prochain horaire demandé.
#>

[CmdletBinding()]
param(
    [Parameter(Mandatory = $true, Position = 0)]
    [string]$BackupFile,
    [Parameter(Mandatory = $true, Position = 1)]
    [ValidatePattern('^([01][0-9]|2[0-3]):[0-5][0-9]$')]
    [string]$Time,
    [switch]$ConfirmRestore,
    [string]$TaskName = 'YELEN SCHOOL - Restauration programmée'
)

$ErrorActionPreference = 'Stop'
$Root = [System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))
$ComposeFile = Join-Path $Root 'docker-compose.client.yml'
$EnvFile = Join-Path $Root '.env'
$RestoreScript = Join-Path $PSScriptRoot 'restore-windows.ps1'
$BackupDirectory = Join-Path $Root 'backups'
$LogFile = Join-Path $BackupDirectory 'restore.log'

function Fail {
    param([string]$Message)
    throw $Message
}

if (-not $ConfirmRestore) {
    Fail 'Confirmation obligatoire : relancez le script avec -ConfirmRestore.'
}
if (-not [System.IO.Path]::IsPathRooted($BackupFile)) {
    $BackupFile = Join-Path $Root $BackupFile
}
$BackupFile = [System.IO.Path]::GetFullPath($BackupFile)
$MediaFile = [System.IO.Path]::ChangeExtension($BackupFile, $null) + '_media.tar.gz'

if (-not (Get-Command Register-ScheduledTask -ErrorAction SilentlyContinue)) {
    Fail 'Le module ScheduledTasks est indisponible sur cette version de Windows.'
}
if (-not (Test-Path $ComposeFile)) { Fail "Fichier introuvable : $ComposeFile" }
if (-not (Test-Path $EnvFile)) { Fail '.env est introuvable. Lancez d’abord l’installation locale.' }
if (-not (Test-Path $RestoreScript)) { Fail "Script introuvable : $RestoreScript" }
if (-not (Test-Path $BackupFile)) { Fail "Dump introuvable : $BackupFile" }
if ((Get-Item $BackupFile).Length -eq 0) { Fail "Dump vide : $BackupFile" }
if (-not (Test-Path $MediaFile)) { Fail "Archive médias introuvable : $MediaFile" }
if ((Get-Item $MediaFile).Length -eq 0) { Fail "Archive médias vide : $MediaFile" }

New-Item -ItemType Directory -Path $BackupDirectory -Force | Out-Null
$requestedTime = [datetime]::ParseExact($Time, 'HH:mm', $null)
$runAt = (Get-Date).Date.AddHours($requestedTime.Hour).AddMinutes($requestedTime.Minute)
if ($runAt -le (Get-Date)) {
    $runAt = $runAt.AddDays(1)
}

# La restauration est volontairement une tâche unique : une restauration
# quotidienne pourrait écraser les nouvelles données de l'établissement.
$arguments = "-NoProfile -ExecutionPolicy Bypass -File `"$RestoreScript`" -BackupFile `"$BackupFile`" -Yes *> `"$LogFile`""
$action = New-ScheduledTaskAction -Execute 'powershell.exe' -Argument $arguments
$trigger = New-ScheduledTaskTrigger -Once -At $runAt
$userId = [System.Security.Principal.WindowsIdentity]::GetCurrent().Name
$principal = New-ScheduledTaskPrincipal -UserId $userId -LogonType InteractiveToken -RunLevel Highest

Register-ScheduledTask `
    -TaskName $TaskName `
    -Action $action `
    -Trigger $trigger `
    -Principal $principal `
    -Description 'Restauration unique et destructive de la base et des médias YELEN SCHOOL' `
    -Force | Out-Null

Write-Host '[OK] Restauration unique programmée.' -ForegroundColor Yellow
Write-Host "Tâche : $TaskName"
Write-Host "Exécution prévue : $runAt"
Write-Host "Sauvegarde : $BackupFile"
Write-Host "Journal : $LogFile"
Write-Host 'Vérifiez la tâche dans le Planificateur de tâches avant son exécution.'
