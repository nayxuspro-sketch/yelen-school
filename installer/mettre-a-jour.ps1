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
.PARAMETER DepuisArchive
    Mise à jour HORS LIGNE : archive fournie par l'éditeur (fichier .bundle) au lieu de GitHub.
    L'empreinte SHA-256 est vérifiée avant toute écriture ; en cas d'écart, rien n'est appliqué.
.PARAMETER Empreinte
    Empreinte SHA-256 attendue de l'archive (64 caractères hexadécimaux). À défaut, le fichier
    <archive>.sha256 placé à côté de l'archive est lu.
.EXAMPLE
    .\mettre-a-jour.bat -DepuisArchive .\yelen-school-5.47.3.bundle
#>

[CmdletBinding()]
param(
    [switch]$SansSauvegarde,
    [ValidateRange(10, 3600)]
    [int]$DelaiAttente = 180,
    [string]$DepuisArchive = '',
    [string]$Empreinte = ''
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

$script:TempArchiveDir = ''

function Expand-ZipMiseAJour {
    # Extrait de façon sûre yelen-school-<version>.bundle (+ .sha256) depuis une archive .zip.
    param([string]$CheminZip)
    Add-Type -AssemblyName System.IO.Compression.FileSystem
    $script:TempArchiveDir = Join-Path $LogDirectory "maj-zip-$PID"
    Remove-Item -LiteralPath $script:TempArchiveDir -Recurse -Force -ErrorAction SilentlyContinue
    New-Item -ItemType Directory -Path $script:TempArchiveDir -Force | Out-Null

    $zip = [System.IO.Compression.ZipFile]::OpenRead($CheminZip)
    try {
        $entreeBundle = $null
        $entreeSha = $null
        foreach ($entree in $zip.Entries) {
            if ([string]::IsNullOrEmpty($entree.Name)) { continue }
            $normalise = $entree.FullName -replace '\\', '/'
            if ($normalise.StartsWith('/') -or ($normalise -split '/') -contains '..') {
                throw "Chemin interdit dans l'archive .zip : $($entree.FullName)"
            }
            if ($entree.Name -match '^yelen-school-\d+\.\d+\.\d+\.bundle$') {
                $entreeBundle = $entree
            }
        }
        if ($null -eq $entreeBundle) {
            throw "Archive .zip incomplète : aucun fichier yelen-school-<version>.bundle trouvé."
        }
        $nomAttenduSha = "$($entreeBundle.Name).sha256"
        foreach ($entree in $zip.Entries) {
            if ($entree.Name -eq $nomAttenduSha) { $entreeSha = $entree; break }
        }
        $cibleBundle = Join-Path $script:TempArchiveDir $entreeBundle.Name
        [System.IO.Compression.ZipFileExtensions]::ExtractToFile($entreeBundle, $cibleBundle, $true)
        if ($null -ne $entreeSha) {
            $cibleSha = Join-Path $script:TempArchiveDir $entreeSha.Name
            [System.IO.Compression.ZipFileExtensions]::ExtractToFile($entreeSha, $cibleSha, $true)
        }
        return $cibleBundle
    } finally {
        $zip.Dispose()
    }
}

function Resolve-ArchiveMiseAJour {
    # Archive de mise à jour hors ligne (.zip ou .bundle git) : l'empreinte SHA-256 est vérifiée avant tout usage,
    # puis le bundle est contrôlé (git bundle verify, qui exige aussi ses prérequis dans le dépôt).
    # Une archive absente, altérée ou incomplète arrête la mise à jour AVANT la sauvegarde et toute écriture.
    param([string]$Chemin, [string]$Empreinte)
    if (-not [System.IO.Path]::IsPathRooted($Chemin)) { $Chemin = Join-Path $Root $Chemin }
    if (-not (Test-Path -LiteralPath $Chemin)) { throw "Archive introuvable : $Chemin" }
    if ([System.IO.Path]::GetExtension($Chemin).ToLower() -eq '.zip') {
        $Chemin = Expand-ZipMiseAJour -CheminZip $Chemin
    }
    $nom = Split-Path -Leaf $Chemin
    $attendu = ($Empreinte -replace '\s', '').ToLower()
    $fichierEmpreinte = "$Chemin.sha256"
    if (-not $attendu -and (Test-Path -LiteralPath $fichierEmpreinte)) {
        $ligne = Get-Content -LiteralPath $fichierEmpreinte -TotalCount 1
        $attendu = (($ligne -split '\s+')[0] -replace '\s', '').ToLower()
    }
    if (-not $attendu) {
        throw "Empreinte SHA-256 absente : placer « $nom.sha256 » à côté de l'archive, ou indiquer -Empreinte."
    }
    if ($attendu -notmatch '^[0-9a-f]{64}$') {
        throw "Empreinte SHA-256 mal formée : 64 caractères hexadécimaux attendus."
    }
    $reel = (Get-FileHash -LiteralPath $Chemin -Algorithm SHA256).Hash.ToLower()
    if ($reel -ne $attendu) {
        throw "Empreinte SHA-256 incorrecte : archive altérée ou incomplète. Mise à jour annulée, rien n'a été modifié."
    }
    Write-Log "Empreinte SHA-256 vérifiée : $reel"
    if ((Invoke-Native { git -C $Root bundle verify --quiet $Chemin }) -ne 0) {
        throw "L'archive n'est pas une mise à jour YELEN SCHOOL valide : mise à jour annulée."
    }
    return $Chemin
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

    if ($DepuisArchive) {
        $ArchivePath = Resolve-ArchiveMiseAJour -Chemin $DepuisArchive -Empreinte $Empreinte
        Write-Log "Mise à jour hors ligne depuis l'archive : $(Split-Path -Leaf $ArchivePath)"
        if ((Invoke-Native { git fetch --quiet $ArchivePath main }) -ne 0) {
            throw 'Archive inutilisable (branche main absente ou dépôt incomplet) : mise à jour annulée.'
        }
    } else {
        Write-Log 'Recherche d''une nouvelle version (GitHub, branche main)...'
        if ((Invoke-Native { git fetch --quiet origin main }) -ne 0) {
            throw 'GitHub injoignable : vérifier la connexion Internet puis réessayer, ou utiliser -DepuisArchive pour une mise à jour hors ligne.'
        }
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
} finally {
    if ($script:TempArchiveDir -and (Test-Path -LiteralPath $script:TempArchiveDir)) {
        Remove-Item -LiteralPath $script:TempArchiveDir -Recurse -Force -ErrorAction SilentlyContinue
    }
}
