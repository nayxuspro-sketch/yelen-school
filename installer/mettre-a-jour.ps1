#requires -Version 5.1
<##
.SYNOPSIS
    Met à jour YELEN SCHOOL (installation Docker) en une seule action.
.DESCRIPTION
    Sauvegarde chiffrée, récupération de la dernière version publiée (GitHub, branche main),
    reconstruction de l'image, redémarrage des services, contrôle de /health/.
    En cas d'échec, la version précédente est rétablie. Journal : logs\mise-a-jour.log.
.PARAMETER SansSauvegarde
    Ne pas lancer installer\backup-windows.ps1 avant la mise à jour.
.PARAMETER DelaiAttente
    Secondes accordées à la nouvelle version pour répondre sur /health/ (migrations comprises).
#>

[CmdletBinding()]
param(
    [switch]$SansSauvegarde,
    [ValidateRange(10, 3600)]
    [int]$DelaiAttente = 180
)

$ErrorActionPreference = 'Stop'
$Root = [System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))
$ComposeFile = Join-Path $Root 'docker-compose.client.yml'
$EnvFile = Join-Path $Root '.env'
$StartScript = Join-Path $PSScriptRoot 'start-local.ps1'
$BackupScript = Join-Path $PSScriptRoot 'backup-windows.ps1'
$LogDirectory = Join-Path $Root 'logs'
$LogFile = Join-Path $LogDirectory 'mise-a-jour.log'

function Write-Log {
    param([string]$Message)
    $line = "$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') $Message"
    Add-Content -Path $LogFile -Value $line -Encoding UTF8
    Write-Host $line
}

function Invoke-Native {
    # Exécute une commande native en affichant sa sortie et ne retourne que son code de retour
    # (sous 'Stop', Windows PowerShell transformerait la progression écrite sur stderr en erreur).
    # La sortie passant par Out-Host n'est pas une console : les commandes docker qui affichent une
    # progression interactive doivent recevoir --progress plain (« failed to get console »).
    param([Parameter(Mandatory = $true)][scriptblock]$Command)
    $ErrorActionPreference = 'Continue'
    & $Command | Out-Host
    $code = $LASTEXITCODE
    $ErrorActionPreference = 'Stop'
    return $code
}

function Get-DotEnvValue {
    param([string]$Name)
    if (-not (Test-Path $EnvFile)) { return '' }
    $line = Get-Content $EnvFile | Where-Object { $_ -match "^$([regex]::Escape($Name))=" } | Select-Object -First 1
    if ($null -eq $line) { return '' }
    return ($line -replace "^$([regex]::Escape($Name))=", '').Trim()
}

function Get-GitOutput {
    param([string[]]$Arguments)
    $ErrorActionPreference = 'Continue'
    $output = (& git @Arguments 2>$null | Out-String).Trim()
    $code = $LASTEXITCODE
    $ErrorActionPreference = 'Stop'
    if ($code -ne 0) { return $null }
    return $output
}

function Get-VersionAt {
    param([string]$Revision)
    $version = Get-GitOutput @('show', "${Revision}:VERSION")
    if ([string]::IsNullOrWhiteSpace($version)) { return '?' }
    return $version
}

function Wait-ForHealth {
    # Attend que /health/ réponde « ok » avec la version attendue (migrations et collecte des
    # fichiers statiques s'exécutent au démarrage du conteneur). Retourne $true en cas de succès.
    param([string]$ExpectedVersion, [int]$TimeoutSeconds = 180)
    $port = Get-DotEnvValue 'YELEN_HTTP_PORT'
    if ([string]::IsNullOrWhiteSpace($port)) { $port = '8000' }
    $url = "http://127.0.0.1:$port/health/"
    $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
    while ((Get-Date) -lt $deadline) {
        try {
            $reponse = Invoke-WebRequest -Uri $url -UseBasicParsing -TimeoutSec 5
            $sante = $reponse.Content | ConvertFrom-Json
            if ($sante.status -eq 'ok' -and $sante.version -eq $ExpectedVersion) { return $true }
        } catch {
            # Service pas encore prêt (connexion refusée, 503) : nouvel essai.
        }
        Start-Sleep -Seconds 5
    }
    return $false
}

function Restore-PreviousVersion {
    # Rétablit le code précédent et, si l'image a déjà été reconstruite, la reconstruit et redémarre.
    param([string]$Commit, [bool]$Rebuild)
    Write-Log "Retour à la version précédente ($Commit)..."
    if ((Invoke-Native { git -C $Root reset --hard $Commit }) -ne 0) {
        Write-Log "ERREUR : retour impossible ; exécuter manuellement : git reset --hard $Commit"
        return
    }
    if ($Rebuild) {
        if ((Invoke-Native { docker compose -f $ComposeFile build --progress plain }) -ne 0) {
            Write-Log 'ERREUR : reconstruction de la version précédente impossible.'
            return
        }
        & powershell.exe -NoProfile -ExecutionPolicy Bypass -File $StartScript
    }
    Write-Log "Version précédente rétablie ($Commit). Journaux : docker compose -f docker-compose.client.yml logs --tail 50 web"
}

New-Item -ItemType Directory -Path $LogDirectory -Force | Out-Null
try {
    foreach ($outil in @('git', 'docker')) {
        if (-not (Get-Command $outil -ErrorAction SilentlyContinue)) { throw "$outil est introuvable dans le PATH." }
    }
    if (-not (Test-Path $EnvFile)) { throw '.env est introuvable. Exécutez demarrage.bat une première fois.' }
    if ((Get-GitOutput @('-C', $Root, 'rev-parse', '--is-inside-work-tree')) -ne 'true') {
        throw "$Root n'est pas un clone git (voir le guide de déploiement, §8)."
    }
    Set-Location $Root

    $commitAvant = Get-GitOutput @('rev-parse', 'HEAD')
    $versionAvant = Get-VersionAt 'HEAD'
    Write-Log "Version installée : $versionAvant ($($commitAvant.Substring(0, 7)))"

    Write-Log 'Recherche d''une nouvelle version (GitHub, branche main)...'
    if ((Invoke-Native { git fetch --quiet origin main }) -ne 0) {
        throw 'GitHub injoignable : vérifier la connexion Internet puis réessayer.'
    }
    $commitCible = Get-GitOutput @('rev-parse', 'FETCH_HEAD')
    if ($commitCible -eq $commitAvant) {
        Write-Log "YELEN SCHOOL est déjà à jour (version $versionAvant)."
        exit 0
    }
    $versionCible = Get-VersionAt 'FETCH_HEAD'
    Write-Log "Nouvelle version disponible : $versionAvant -> $versionCible ($($commitCible.Substring(0, 7)))"
    $changements = Get-GitOutput @('log', '--oneline', '--no-decorate', '-15', 'HEAD..FETCH_HEAD')
    if ($changements) { Write-Host $changements }

    if (-not $SansSauvegarde) {
        Write-Log 'Sauvegarde chiffrée avant mise à jour...'
        & powershell.exe -NoProfile -ExecutionPolicy Bypass -File $BackupScript
        if ($LASTEXITCODE -ne 0) {
            throw 'La sauvegarde a échoué : mise à jour annulée (services inchangés). Relancer avec -SansSauvegarde pour passer outre.'
        }
    }

    # Les fichiers de documentation peuvent apparaître modifiés (fins de ligne) : ils sont remis
    # à l'état du dépôt ; toute autre modification locale bloque volontairement l'avance rapide.
    [void](Invoke-Native { git checkout --quiet -- docs })
    if ((Invoke-Native { git merge --ff-only FETCH_HEAD }) -ne 0) {
        throw 'Des fichiers ont été modifiés localement (git status) : mise à jour annulée.'
    }
    [void](Invoke-Native { git checkout --quiet -- docs })

    Write-Log 'Reconstruction de l''image (plusieurs minutes)...'
    if ((Invoke-Native { docker compose -f $ComposeFile build --progress plain }) -ne 0) {
        Write-Log 'ERREUR : la reconstruction a échoué ; les services en cours ne sont pas touchés.'
        Restore-PreviousVersion -Commit $commitAvant -Rebuild $false
        exit 1
    }

    Write-Log 'Redémarrage des services...'
    & powershell.exe -NoProfile -ExecutionPolicy Bypass -File $StartScript
    $demarrageOk = ($LASTEXITCODE -eq 0)

    if (-not $demarrageOk -or -not (Wait-ForHealth -ExpectedVersion $versionCible -TimeoutSeconds $DelaiAttente)) {
        Write-Log 'ERREUR : la nouvelle version ne répond pas correctement (/health/).'
        [void](Invoke-Native { docker compose -f $ComposeFile logs --tail 30 web })
        Restore-PreviousVersion -Commit $commitAvant -Rebuild $true
        Write-Log 'Si la base a été migrée par la nouvelle version, restaurer la sauvegarde créée avant la mise à jour (installer\restore-windows.bat).'
        exit 1
    }

    Write-Log "Mise à jour terminée : version $versionCible ($($commitCible.Substring(0, 7))). Les postes connectés se rafraîchissent automatiquement à leur prochaine page."
    [void](Invoke-Native { docker compose -f $ComposeFile ps })
} catch {
    Write-Log "ERREUR : $($_.Exception.Message)"
    exit 1
}
