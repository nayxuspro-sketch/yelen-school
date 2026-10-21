#requires -Version 5.1
<##
.SYNOPSIS
    Déverrouille le dossier YELEN SCHOOL pour une maintenance (inverse de verrouiller-serveur.ps1).

.DESCRIPTION
    Rétablit l'héritage des permissions NTFS depuis le dossier parent pour tout
    le dossier et le fichier .env, et retire les règles d'audit posées par
    verrouiller-serveur.ps1. Ré-exécuter verrouiller-serveur.bat à la fin de
    l'intervention. À exécuter en tant qu'administrateur (deverrouiller-serveur.bat).

.PARAMETER Dossier
    Dossier de l'application (défaut : dossier parent de installer\).
#>
[CmdletBinding()]
param(
    [string]$Dossier = ''
)

$ErrorActionPreference = 'Stop'

$identite = [Security.Principal.WindowsIdentity]::GetCurrent()
$estAdmin = (New-Object Security.Principal.WindowsPrincipal($identite)).IsInRole(
    [Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $estAdmin) {
    Write-Host '[ERREUR] Ce script doit être exécuté en tant qu''administrateur (deverrouiller-serveur.bat).' -ForegroundColor Red
    exit 1
}

if ([string]::IsNullOrWhiteSpace($Dossier)) {
    $Dossier = [System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..\..'))
}
$Dossier = $Dossier.TrimEnd('\')
if (-not (Test-Path (Join-Path $Dossier 'manage.py'))) {
    Write-Host "[ERREUR] $Dossier ne ressemble pas au dossier YELEN SCHOOL (manage.py introuvable)." -ForegroundColor Red
    exit 1
}
$FichierEnv = Join-Path $Dossier '.env'

Write-Host '================================================================' -ForegroundColor Yellow
Write-Host '  YELEN SCHOOL — DÉVERROUILLAGE DU SERVEUR (maintenance)' -ForegroundColor Yellow
Write-Host '================================================================' -ForegroundColor Yellow
Write-Host "Dossier : $Dossier"

Write-Host '[1/2] Rétablissement de l''héritage des permissions NTFS...' -ForegroundColor Cyan
& icacls $Dossier /inheritance:e | Out-Null
& icacls $Dossier /reset /T /C /Q | Out-Null
if (Test-Path $FichierEnv) {
    & icacls $FichierEnv /reset | Out-Null
}
Write-Host '      OK' -ForegroundColor Green

Write-Host '[2/2] Suppression des règles d''audit...' -ForegroundColor Cyan
try {
    foreach ($chemin in @($Dossier, $FichierEnv)) {
        if (-not (Test-Path $chemin)) { continue }
        $acl = Get-Acl -Path $chemin -Audit
        foreach ($regle in @($acl.GetAuditRules($true, $false, [System.Security.Principal.SecurityIdentifier]))) {
            $acl.RemoveAuditRuleAll($regle)
        }
        Set-Acl -Path $chemin -AclObject $acl
    }
    Write-Host '      OK' -ForegroundColor Green
} catch {
    Write-Host "      AVERTISSEMENT : $($_.Exception.Message)" -ForegroundColor Yellow
}

Write-Host ''
Write-Host 'Dossier déverrouillé. Ré-exécutez verrouiller-serveur.bat avant de quitter.' -ForegroundColor Yellow
