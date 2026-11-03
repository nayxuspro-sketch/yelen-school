#requires -Version 5.1
<##
.SYNOPSIS
    Programme l'agent hôte de mise à jour (appliquer-mise-a-jour-en-attente.ps1) sans fenêtre console.
#>
[CmdletBinding()]
param(
    [switch]$Force,
    [string]$TaskName = 'YELEN SCHOOL - Agent de mise a jour'
)

$ErrorActionPreference = 'Stop'
$AgentScript = Join-Path $PSScriptRoot 'appliquer-mise-a-jour-en-attente.ps1'
$TaskHelper = Join-Path $PSScriptRoot 'yelen-scheduled-task.ps1'

if (-not (Get-Command Register-ScheduledTask -ErrorAction SilentlyContinue)) { exit 0 }
if (-not (Test-Path -LiteralPath $AgentScript)) { exit 0 }
if (-not (Test-Path -LiteralPath $TaskHelper)) { exit 0 }
. $TaskHelper

# Met à niveau silencieusement toute tâche YELEN existante encore liée directement à powershell.exe.
[void](Update-YelenTasksHeadless)

$existante = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
if ($null -ne $existante) {
    if ($existante.State -eq 'Running') { exit 0 }
    # Une ancienne inscription en LogonType S4U bloque Windows Credential Manager (git fetch sur dépôt privé)
    # et le contexte Docker Desktop utilisateur : elle est réparée automatiquement vers Interactive.
    $logonConforme = ([string]$existante.Principal.LogonType -match '^Interactive')
    if (-not $Force -and $logonConforme) { exit 0 }
}

$estAdmin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole(
    [Security.Principal.WindowsBuiltInRole]::Administrator
)
$userId = [System.Security.Principal.WindowsIdentity]::GetCurrent().Name
$arguments = "-NoProfile -NonInteractive -ExecutionPolicy Bypass -WindowStyle Hidden -File `"$AgentScript`""
$action = New-YelenHeadlessTaskAction -PowerShellArguments $arguments -WorkingDirectory (Split-Path -Parent $PSScriptRoot)
$trigger = New-ScheduledTaskTrigger -Once -At (Get-Date).AddSeconds(5) `
    -RepetitionInterval (New-TimeSpan -Minutes 1) -RepetitionDuration (New-TimeSpan -Days 3650)

# LogonType Interactive indispensable pour accéder au Gestionnaire d'identification Windows (jeton GitHub)
# ainsi qu'au moteur Docker Desktop de la session ouverte.
if ($estAdmin) {
    $principal = New-ScheduledTaskPrincipal -UserId $userId -LogonType Interactive -RunLevel Highest
} else {
    $principal = New-ScheduledTaskPrincipal -UserId $userId -LogonType Interactive -RunLevel Limited
}

$settings = New-ScheduledTaskSettingsSet -MultipleInstances IgnoreNew `
    -ExecutionTimeLimit (New-TimeSpan -Minutes 30) `
    -StartWhenAvailable -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries

try {
    Register-ScheduledTask `
        -TaskName $TaskName `
        -Action $action `
        -Trigger $trigger `
        -Principal $principal `
        -Settings $settings `
        -Description 'Applique sans fenêtre les mises à jour demandées depuis Configuration' `
        -Force -ErrorAction Stop | Out-Null
    Start-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
} catch {
    # Si une tâche existante avait été créée avec RunLevel Highest et qu'on tourne sans élévation, ne pas bloquer.
}
