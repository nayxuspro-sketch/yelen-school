#requires -Version 5.1
<##
.SYNOPSIS
    Autorise l'accès réseau local à YELEN SCHOOL dans le pare-feu Windows.

.DESCRIPTION
    Crée ou remplace une règle entrante TCP limitée aux profils réseau privé ou
    domaine et aux adresses du sous-réseau local. Le script se relance avec élévation UAC
    lorsque nécessaire.

.EXAMPLE
    .\configure-firewall.ps1 -Port 8000
#>

[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [ValidateRange(1, 65535)]
    [int]$Port,

    [switch]$Remove
)

$ErrorActionPreference = 'Stop'
$ScriptPath = $PSCommandPath
$RuleName = 'YELEN_SCHOOL_LocalWeb'
$DisplayName = 'YELEN SCHOOL - Accès réseau local'
$RuleGroup = 'YELEN SCHOOL'

function Test-IsAdministrator {
    $identity = [Security.Principal.WindowsIdentity]::GetCurrent()
    $principal = New-Object Security.Principal.WindowsPrincipal($identity)
    return $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
}

function Invoke-Elevated {
    $arguments = "-NoProfile -ExecutionPolicy Bypass -File `"$script:ScriptPath`" -Port $Port"
    if ($Remove) {
        $arguments += ' -Remove'
    }

    try {
        $process = Start-Process `
            -FilePath 'powershell.exe' `
            -ArgumentList $arguments `
            -Verb RunAs `
            -Wait `
            -PassThru
        if ($null -eq $process) {
            return 1
        }
        return $process.ExitCode
    } catch {
        Write-Host "[ERREUR] L'autorisation administrateur est nécessaire pour configurer le pare-feu : $($_.Exception.Message)" -ForegroundColor Red
        return 1
    }
}

try {
    if (-not (Test-IsAdministrator)) {
        Write-Host '[INFO] Une confirmation UAC est nécessaire pour autoriser l’accès réseau local.' -ForegroundColor Yellow
        exit (Invoke-Elevated)
    }

    if (-not (Get-Command Get-NetFirewallRule -ErrorAction SilentlyContinue)) {
        throw 'Les cmdlets du pare-feu Windows sont indisponibles sur cette version de Windows.'
    }

    # Le nom stable permet de remplacer automatiquement une ancienne règle
    # lorsque le port YELEN_HTTP_PORT est modifié.
    $existingRules = @(Get-NetFirewallRule -Name $RuleName -ErrorAction SilentlyContinue)
    if ($existingRules.Count -gt 0) {
        $existingRules | Remove-NetFirewallRule -ErrorAction Stop
    }

    if ($Remove) {
        Write-Host "[OK] Règle de pare-feu supprimée : $DisplayName" -ForegroundColor Green
        exit 0
    }

    New-NetFirewallRule `
        -Name $RuleName `
        -DisplayName $DisplayName `
        -Description "Autorise YELEN SCHOOL sur le port TCP $Port depuis le réseau local." `
        -Group $RuleGroup `
        -Direction Inbound `
        -Action Allow `
        -Protocol TCP `
        -LocalPort $Port `
        -Profile Private,Domain `
        -RemoteAddress LocalSubnet `
        -Enabled True `
        -EdgeTraversalPolicy Block `
        -ErrorAction Stop | Out-Null

    Write-Host "[OK] Pare-feu Windows : TCP $Port autorisé sur le réseau privé local." -ForegroundColor Green
    exit 0
} catch {
    Write-Host "[ERREUR] Configuration du pare-feu impossible : $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}
