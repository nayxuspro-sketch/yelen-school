#requires -Version 5.1
<##
.SYNOPSIS
    Programme la vérification des paiements Mobile Money en ligne (CinetPay) toutes les 10 minutes.
#>
[CmdletBinding()]
param(
    [ValidateRange(2, 60)]
    [int]$Minutes = 10,
    [string]$TaskName = 'YELEN SCHOOL - Paiements Mobile Money en ligne'
)

$ErrorActionPreference = 'Stop'
$Root = [System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))
$Script = Join-Path $PSScriptRoot 'verifier-paiements-mobiles.ps1'
$LogDirectory = Join-Path $Root 'logs'

if (-not (Get-Command Register-ScheduledTask -ErrorAction SilentlyContinue)) {
    throw 'Le module ScheduledTasks est indisponible sur cette version de Windows.'
}
if (-not (Test-Path $Script)) {
    throw "Script introuvable : $Script"
}
New-Item -ItemType Directory -Path $LogDirectory -Force | Out-Null

$arguments = "-NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File `"$Script`""
$action = New-ScheduledTaskAction -Execute 'powershell.exe' -Argument $arguments
# En arrière-plan (S4U, sans mot de passe enregistré) : aucune fenêtre dans la session ouverte.
$userId = [System.Security.Principal.WindowsIdentity]::GetCurrent().Name
$trigger = New-ScheduledTaskTrigger -Once -At (Get-Date).AddMinutes(1) `
    -RepetitionInterval (New-TimeSpan -Minutes $Minutes) -RepetitionDuration (New-TimeSpan -Days 3650)
$principal = New-ScheduledTaskPrincipal -UserId $userId -LogonType S4U -RunLevel Highest
$settings = New-ScheduledTaskSettingsSet -MultipleInstances IgnoreNew -ExecutionTimeLimit (New-TimeSpan -Minutes 10) `
    -StartWhenAvailable -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries

Register-ScheduledTask `
    -TaskName $TaskName `
    -Action $action `
    -Trigger $trigger `
    -Principal $principal `
    -Settings $settings `
    -Description 'Vérifie auprès de CinetPay les paiements Mobile Money en ligne en attente et les confirme' `
    -Force | Out-Null

Write-Host "[OK] Vérification des paiements en ligne programmée toutes les $Minutes minutes (en arrière-plan, sans fenêtre)." -ForegroundColor Green
Write-Host "Tâche : $TaskName"
Write-Host "Journal : $LogDirectory\paiements-en-ligne.log"
Write-Host 'Dans .env : CINETPAY_API_KEY, CINETPAY_SITE_ID, CINETPAY_URL_PUBLIQUE.'
