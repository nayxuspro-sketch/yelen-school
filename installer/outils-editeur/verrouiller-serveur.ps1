#requires -Version 5.1
<##
.SYNOPSIS
    Verrouille le dossier YELEN SCHOOL sur le serveur du client (après déploiement).

.DESCRIPTION
    Couche « système » de la protection anti-copie, complémentaire de la licence
    signée et liée au serveur (voir docs/GUIDE_DEPLOIEMENT_WINDOWS.md §3.5) :

      1. Permissions NTFS du dossier : héritage supprimé, contrôle total réservé à
         SYSTEM, au groupe Administrateurs et au(x) compte(s) d'exploitation du
         serveur (par défaut le compte qui exécute ce script). Tout autre
         utilisateur ne peut ni ouvrir, ni lire, ni copier le dossier.
      2. Fichier .env (secrets, clé publique de licence) : mêmes droits,
         explicitement.
      3. Partages réseau exposant le dossier : supprimés.
      4. Audit NTFS : tentatives d'accès refusées sur le dossier et lectures
         réussies du .env journalisées (Observateur d'événements → Sécurité,
         événement 4663).
      5. État BitLocker du disque : vérifié et recommandé (non activé par ce
         script — le chiffrement est une décision du client, avec sauvegarde de
         la clé de récupération).
      6. Rappel des comptes administrateurs locaux : un administrateur peut
         toujours copier le dossier ; la copie est inutilisable ailleurs grâce
         à la liaison de la licence au serveur, mais le nombre de comptes
         administrateurs doit rester minimal.

    Les groupes sont désignés par leur SID : le script fonctionne sur Windows
    en français comme en anglais. À exécuter en tant qu'administrateur
    (verrouiller-serveur.bat). Réversible avec deverrouiller-serveur.ps1.

.PARAMETER Dossier
    Dossier de l'application (défaut : dossier parent de installer\).

.PARAMETER ComptesAutorises
    Comptes (DOMAINE\nom ou nom local) conservant le contrôle total en plus de
    SYSTEM et des Administrateurs — ceux qui démarrent Docker Desktop et
    exécutent les mises à jour. Défaut : le compte courant.
#>
[CmdletBinding()]
param(
    [string]$Dossier = '',
    [string[]]$ComptesAutorises = @()
)

$ErrorActionPreference = 'Stop'

function Test-Administrateur {
    $identite = [Security.Principal.WindowsIdentity]::GetCurrent()
    return (New-Object Security.Principal.WindowsPrincipal($identite)).IsInRole(
        [Security.Principal.WindowsBuiltInRole]::Administrator)
}

function Resolve-Compte {
    param([string]$Nom)
    try {
        $compte = New-Object System.Security.Principal.NTAccount($Nom)
        return $compte.Translate([System.Security.Principal.SecurityIdentifier])
    } catch {
        throw "Compte introuvable : $Nom"
    }
}

if (-not (Test-Administrateur)) {
    Write-Host '[ERREUR] Ce script doit être exécuté en tant qu''administrateur (verrouiller-serveur.bat).' -ForegroundColor Red
    exit 1
}

if ([string]::IsNullOrWhiteSpace($Dossier)) {
    $Dossier = [System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..\..'))
}
$Dossier = $Dossier.TrimEnd('\')
if (-not (Test-Path (Join-Path $Dossier 'docker-compose.client.yml')) -and -not (Test-Path (Join-Path $Dossier 'manage.py'))) {
    Write-Host "[ERREUR] $Dossier ne ressemble pas au dossier YELEN SCHOOL (manage.py introuvable)." -ForegroundColor Red
    exit 1
}
$FichierEnv = Join-Path $Dossier '.env'

$SidSysteme = New-Object System.Security.Principal.SecurityIdentifier('S-1-5-18')
$SidAdministrateurs = New-Object System.Security.Principal.SecurityIdentifier('S-1-5-32-544')
$SidToutLeMonde = New-Object System.Security.Principal.SecurityIdentifier('S-1-1-0')

if ($ComptesAutorises.Count -eq 0) {
    $ComptesAutorises = @([Security.Principal.WindowsIdentity]::GetCurrent().Name)
}
$SidsAutorises = @($ComptesAutorises | ForEach-Object { Resolve-Compte $_ })

Write-Host '================================================================' -ForegroundColor Cyan
Write-Host '  YELEN SCHOOL — VERROUILLAGE DU SERVEUR' -ForegroundColor Cyan
Write-Host '================================================================' -ForegroundColor Cyan
Write-Host "Dossier            : $Dossier"
Write-Host "Comptes conservés  : SYSTEM, Administrateurs, $($ComptesAutorises -join ', ')"
Write-Host ''

# ── 1. Permissions NTFS du dossier ─────────────────────────────────────────
Write-Host '[1/6] Permissions NTFS du dossier...' -ForegroundColor Cyan
& icacls $Dossier /reset /T /C /Q | Out-Null
$droits = @("*$($SidSysteme.Value):(OI)(CI)F", "*$($SidAdministrateurs.Value):(OI)(CI)F")
foreach ($sid in $SidsAutorises) { $droits += "*$($sid.Value):(OI)(CI)F" }
$arguments = @($Dossier, '/inheritance:r', '/grant:r') + $droits
& icacls @arguments | Out-Null
if ($LASTEXITCODE -ne 0) { throw 'icacls a échoué sur le dossier.' }
Write-Host '      OK — héritage supprimé, accès réservé aux comptes listés.' -ForegroundColor Green

# ── 2. Fichier .env ────────────────────────────────────────────────────────
Write-Host '[2/6] Fichier .env...' -ForegroundColor Cyan
if (Test-Path $FichierEnv) {
    $droitsEnv = @("*$($SidSysteme.Value):F", "*$($SidAdministrateurs.Value):F")
    foreach ($sid in $SidsAutorises) { $droitsEnv += "*$($sid.Value):F" }
    $arguments = @($FichierEnv, '/inheritance:r', '/grant:r') + $droitsEnv
    & icacls @arguments | Out-Null
    if ($LASTEXITCODE -ne 0) { throw 'icacls a échoué sur .env.' }
    Write-Host '      OK — .env protégé explicitement.' -ForegroundColor Green
} else {
    Write-Host '      .env absent : ignoré.' -ForegroundColor Yellow
}

# ── 3. Partages réseau ─────────────────────────────────────────────────────
Write-Host '[3/6] Partages réseau exposant le dossier...' -ForegroundColor Cyan
$partages = @()
if (Get-Command Get-SmbShare -ErrorAction SilentlyContinue) {
    $partages = @(Get-SmbShare -ErrorAction SilentlyContinue | Where-Object {
        $_.Path -and ($Dossier.StartsWith($_.Path.TrimEnd('\'), [StringComparison]::OrdinalIgnoreCase) -or
                      $_.Path.StartsWith($Dossier, [StringComparison]::OrdinalIgnoreCase)) -and
        $_.Name -notmatch '^[A-Z]\$$' -and $_.Name -ne 'ADMIN$'
    })
}
if ($partages.Count -eq 0) {
    Write-Host '      OK — aucun partage.' -ForegroundColor Green
} else {
    foreach ($partage in $partages) {
        Remove-SmbShare -Name $partage.Name -Force
        Write-Host "      Partage supprimé : $($partage.Name) ($($partage.Path))" -ForegroundColor Yellow
    }
}

# ── 4. Audit NTFS ──────────────────────────────────────────────────────────
Write-Host '[4/6] Audit NTFS (journal Sécurité, événement 4663)...' -ForegroundColor Cyan
try {
    # Sous-catégorie « Système de fichiers » désignée par son GUID (indépendant de la langue).
    & auditpol /set /subcategory:"{0CCE921D-69AE-11D9-BED3-505054503030}" /success:enable /failure:enable | Out-Null
    $droitsLecture = [System.Security.AccessControl.FileSystemRights]'ReadData, ReadAttributes, ReadExtendedAttributes, ExecuteFile'
    $heritage = [System.Security.AccessControl.InheritanceFlags]'ContainerInherit, ObjectInherit'
    $aucune = [System.Security.AccessControl.PropagationFlags]::None

    $acl = Get-Acl -Path $Dossier -Audit
    foreach ($regle in @($acl.GetAuditRules($true, $false, [System.Security.Principal.SecurityIdentifier]))) {
        $acl.RemoveAuditRuleAll($regle)
    }
    $acl.AddAuditRule((New-Object System.Security.AccessControl.FileSystemAuditRule(
        $SidToutLeMonde, $droitsLecture, $heritage, $aucune, [System.Security.AccessControl.AuditFlags]::Failure)))
    Set-Acl -Path $Dossier -AclObject $acl

    if (Test-Path $FichierEnv) {
        $aclEnv = Get-Acl -Path $FichierEnv -Audit
        foreach ($regle in @($aclEnv.GetAuditRules($true, $false, [System.Security.Principal.SecurityIdentifier]))) {
            $aclEnv.RemoveAuditRuleAll($regle)
        }
        $aclEnv.AddAuditRule((New-Object System.Security.AccessControl.FileSystemAuditRule(
            $SidToutLeMonde, [System.Security.AccessControl.FileSystemRights]::ReadData,
            [System.Security.AccessControl.InheritanceFlags]::None, $aucune,
            [System.Security.AccessControl.AuditFlags]'Success, Failure')))
        Set-Acl -Path $FichierEnv -AclObject $aclEnv
    }
    Write-Host '      OK — accès refusés au dossier et lectures du .env journalisés.' -ForegroundColor Green
} catch {
    Write-Host "      AVERTISSEMENT : audit non configuré ($($_.Exception.Message))." -ForegroundColor Yellow
}

# ── 5. BitLocker ───────────────────────────────────────────────────────────
Write-Host '[5/6] Chiffrement du disque (BitLocker)...' -ForegroundColor Cyan
$lecteur = [System.IO.Path]::GetPathRoot($Dossier).TrimEnd('\')
$etatBitLocker = $null
if (Get-Command Get-BitLockerVolume -ErrorAction SilentlyContinue) {
    try { $etatBitLocker = Get-BitLockerVolume -MountPoint $lecteur -ErrorAction Stop } catch { $etatBitLocker = $null }
}
if ($etatBitLocker -and "$($etatBitLocker.ProtectionStatus)" -eq 'On') {
    Write-Host "      OK — BitLocker actif sur $lecteur." -ForegroundColor Green
} else {
    Write-Host "      RECOMMANDÉ — BitLocker n'est pas actif sur $lecteur : un disque retiré ou démarré" -ForegroundColor Yellow
    Write-Host '      sur un autre système reste lisible. Activation (édition Pro/Entreprise) :' -ForegroundColor Yellow
    Write-Host "        Paramètres > Confidentialité et sécurité > Chiffrement de l'appareil / BitLocker," -ForegroundColor Yellow
    Write-Host "        ou : manage-bde -on $lecteur -RecoveryPassword   (conserver la clé de récupération hors du serveur)." -ForegroundColor Yellow
}

# ── 6. Comptes administrateurs locaux ──────────────────────────────────────
Write-Host '[6/6] Comptes administrateurs locaux...' -ForegroundColor Cyan
try {
    $membres = @(Get-LocalGroupMember -SID 'S-1-5-32-544' -ErrorAction Stop | ForEach-Object { $_.Name })
    Write-Host "      Membres : $($membres -join ', ')"
} catch {
    Write-Host '      Liste indisponible sur cette édition de Windows.' -ForegroundColor Yellow
}
Write-Host '      Rappel : un administrateur peut toujours copier le dossier ; la copie est inutilisable' -ForegroundColor Yellow
Write-Host '      ailleurs (licence liée au serveur), mais limitez les comptes administrateurs au strict' -ForegroundColor Yellow
Write-Host '      nécessaire et donnez au personnel des comptes Windows standards.' -ForegroundColor Yellow

Write-Host ''
Write-Host '================================================================' -ForegroundColor Green
Write-Host '  Serveur verrouillé. Pour une maintenance : deverrouiller-serveur.bat,' -ForegroundColor Green
Write-Host '  puis ré-exécuter verrouiller-serveur.bat avant de quitter.' -ForegroundColor Green
Write-Host '================================================================' -ForegroundColor Green
