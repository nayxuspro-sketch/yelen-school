#requires -Version 5.1
<##
.SYNOPSIS
    Applique automatiquement une mise à jour en ligne ou par archive .zip demandée depuis Configuration.
.DESCRIPTION
    Surveille mises-a-jour\demande.json :
      - Mode EN_LIGNE (statut VERIFICATION ou EN_ATTENTE) : interroge origin/main avec git fetch ;
        s'il n'y a aucune version plus récente, consigne AUCUNE_MAJ sans rien redémarrer ; sinon
        consigne EN_COURS avec la version cible puis exécute installer\mettre-a-jour.ps1.
      - Mode ARCHIVE (statut EN_ATTENTE) : valide strictement le nom du bundle et l'empreinte SHA-256,
        puis exécute installer\mettre-a-jour.ps1 -DepuisArchive.
#>
[CmdletBinding()]
param(
    [switch]$UnePasse
)

$ErrorActionPreference = 'Stop'
$Root = [System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))
$EnvFile = Join-Path $Root '.env'
$UpdateDir = Join-Path $Root 'mises-a-jour'
$DemandeFile = Join-Path $UpdateDir 'demande.json'
$UpdateScript = Join-Path $PSScriptRoot 'mettre-a-jour.ps1'
$LogDirectory = Join-Path $Root 'logs'
$UpdateLog = Join-Path $LogDirectory 'mise-a-jour.log'

function Initialize-HostEnvironment {
    # En tâche planifiée sans fenêtre (conhost --headless), compléter le PATH standard et interdire
    # toute invite interactive Git Credential Manager ou UAC bloquante.
    $sep = [System.IO.Path]::PathSeparator
    $candidats = @()
    if ($env:ProgramFiles) {
        $candidats += (Join-Path $env:ProgramFiles 'Git\cmd')
        $candidats += (Join-Path $env:ProgramFiles 'Git\bin')
        $candidats += (Join-Path $env:ProgramFiles 'Docker\Docker\resources\bin')
    }
    if ($env:LOCALAPPDATA) {
        $candidats += (Join-Path $env:LOCALAPPDATA 'Programs\Git\cmd')
    }
    $actuels = @($env:PATH -split [regex]::Escape([string]$sep) | Where-Object { $_ })
    foreach ($dossier in $candidats) {
        if ($dossier -and (Test-Path -LiteralPath $dossier) -and ($actuels -notcontains $dossier)) {
            $env:PATH = "$dossier$sep$env:PATH"
        }
    }
    $env:GIT_TERMINAL_PROMPT = '0'
    $env:GCM_INTERACTIVE = 'never'
    $env:YELEN_UNATTENDED = '1'
    # Évite « fatal: detected dubious ownership » si le propriétaire NTFS diffère du compte de la tâche.
    $env:GIT_CONFIG_COUNT = '1'
    $env:GIT_CONFIG_KEY_0 = 'safe.directory'
    $env:GIT_CONFIG_VALUE_0 = '*'
}

function Get-DotEnvValue {
    param([string]$Name)
    if (-not (Test-Path -LiteralPath $EnvFile)) { return '' }
    $line = Get-Content -LiteralPath $EnvFile | Where-Object { $_ -match "^$([regex]::Escape($Name))=" } | Select-Object -First 1
    if ($null -eq $line) { return '' }
    return ($line -replace "^$([regex]::Escape($Name))=", '').Trim()
}

function Write-AgentLog {
    param([string]$Message)
    try {
        New-Item -ItemType Directory -Path $LogDirectory -Force | Out-Null
        $clean = $Message -replace 'https://[^@\s]+@', 'https://***@'
        Add-Content -LiteralPath $UpdateLog -Value "$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') [AGENT] $clean" -Encoding UTF8
    } catch { }
}

function Save-DemandeAtomique {
    param([hashtable]$Donnees)
    New-Item -ItemType Directory -Path $UpdateDir -Force | Out-Null
    $tmp = Join-Path $UpdateDir ".demande.$PID.tmp"
    $json = $Donnees | ConvertTo-Json -Depth 4
    [System.IO.File]::WriteAllText($tmp, "$json`n", (New-Object System.Text.UTF8Encoding($false)))
    try {
        for ($essai = 1; $essai -le 5; $essai++) {
            try {
                Move-Item -LiteralPath $tmp -Destination $DemandeFile -Force -ErrorAction Stop
                return
            } catch {
                if ($essai -eq 5) {
                    [System.IO.File]::Copy($tmp, $DemandeFile, $true)
                    return
                }
                Start-Sleep -Milliseconds 80
            }
        }
    } finally {
        if (Test-Path -LiteralPath $tmp) {
            Remove-Item -LiteralPath $tmp -Force -ErrorAction SilentlyContinue
        }
    }
}

function Invoke-GitFetchOnline {
    # Tente d'abord avec les identifiants Git de la session Windows ; en cas d'échec, essaie un jeton
    # optionnel YELEN_GITHUB_TOKEN du .env uniquement en mémoire (sans rien écrire dans .git/config).
    if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
        return @{ Code = 127; Detail = 'git introuvable dans le PATH' }
    }

    $ErrorActionPreference = 'Continue'
    $sortie = (& git -C $Root fetch --quiet origin main 2>&1 | Out-String).Trim()
    $code = $LASTEXITCODE
    $ErrorActionPreference = 'Stop'
    if ($code -eq 0) {
        return @{ Code = 0; Detail = '' }
    }

    $jeton = Get-DotEnvValue 'YELEN_GITHUB_TOKEN'
    if (-not [string]::IsNullOrWhiteSpace($jeton)) {
        $b64 = [Convert]::ToBase64String([Text.Encoding]::ASCII.GetBytes("x-access-token:$jeton"))
        $env:GIT_CONFIG_COUNT = '2'
        $env:GIT_CONFIG_KEY_1 = 'http.https://github.com/.extraheader'
        $env:GIT_CONFIG_VALUE_1 = "AUTHORIZATION: basic $b64"
        $ErrorActionPreference = 'Continue'
        $sortie = (& git -C $Root fetch --quiet origin main 2>&1 | Out-String).Trim()
        $code = $LASTEXITCODE
        $ErrorActionPreference = 'Stop'
        if ($code -eq 0) {
            # Conserve l'en-tête en mémoire pour le sous-processus mettre-a-jour.ps1.
            return @{ Code = 0; Detail = '' }
        }
        $env:GIT_CONFIG_COUNT = '1'
        Remove-Item Env:GIT_CONFIG_KEY_1, Env:GIT_CONFIG_VALUE_1 -ErrorAction SilentlyContinue
    }

    $nettoye = ($sortie -replace 'https://[^@\s]+@', 'https://***@' -replace '\r?\n', ' ').Trim()
    return @{ Code = $code; Detail = $nettoye }
}

function Format-ErreurFetch {
    param([int]$Code, [string]$Detail)
    if ($Code -eq 127) {
        return "Git est introuvable sur le serveur Windows : vérifiez l'installation de Git ou utilisez le bouton Mise à jour (.zip)."
    }
    if ($Detail -match 'Authentication failed|could not read Username|terminal prompts disabled|Logon failed|403|401|Repository not found|no such logon session') {
        return "Authentification GitHub refusée sur le serveur Windows (dépôt privé) : lancez une fois C:\YELEN-SCHOOL\mettre-a-jour.bat sur le PC serveur pour actualiser l'accès Git, ou utilisez le bouton Mise à jour (.zip)."
    }
    return 'Dépôt GitHub injoignable : vérifiez la connexion Internet ou utilisez le bouton Mise à jour (.zip).'
}

function Get-DerniereErreurJournal {
    $defaut = 'La mise à jour a échoué (consulter logs\mise-a-jour.log).'
    if (Test-Path -LiteralPath $UpdateLog) {
        $derniereLigne = Get-Content -LiteralPath $UpdateLog -Tail 20 |
            Where-Object { $_ -match 'ERREUR' } | Select-Object -Last 1
        if ($derniereLigne) { return $derniereLigne }
    }
    return $defaut
}

function Test-VersionSuperieure {
    param([string]$Cible, [string]$Actuelle)
    if ([string]::IsNullOrWhiteSpace($Cible)) { return $false }
    if ($Cible -eq $Actuelle) { return $false }
    try {
        return ([version]$Cible -gt [version]$Actuelle)
    } catch {
        return ($Cible -ne $Actuelle)
    }
}

function Invoke-TraitementDemande {
    if (-not (Test-Path -LiteralPath $DemandeFile)) { return $null }

    try {
        $brut = [System.IO.File]::ReadAllText($DemandeFile, [System.Text.Encoding]::UTF8)
        $demandeObj = $brut | ConvertFrom-Json
    } catch {
        return $null
    }
    if ($null -eq $demandeObj -or $demandeObj.statut -notin @('VERIFICATION', 'EN_ATTENTE')) {
        return $null
    }

    $donnees = @{}
    foreach ($prop in $demandeObj.PSObject.Properties) {
        $donnees[$prop.Name] = $prop.Value
    }

    if ([string]$donnees['mode'] -eq 'EN_LIGNE') {
        $fetch = Invoke-GitFetchOnline
        if ($fetch.Code -ne 0) {
            Write-AgentLog "ERREUR : git fetch origin main a échoué (code $($fetch.Code)) : $($fetch.Detail)"
            $donnees['statut'] = 'ECHEC'
            $donnees['fin_le'] = (Get-Date).ToString('o')
            $donnees['message'] = Format-ErreurFetch -Code $fetch.Code -Detail $fetch.Detail
            Save-DemandeAtomique $donnees
            return 1
        }

        $ErrorActionPreference = 'Continue'
        $commitAvant = (& git -C $Root rev-parse HEAD 2>$null | Out-String).Trim()
        $commitCible = (& git -C $Root rev-parse FETCH_HEAD 2>$null | Out-String).Trim()
        $versionAvant = (& git -C $Root show HEAD:VERSION 2>$null | Out-String).Trim()
        $versionCible = (& git -C $Root show FETCH_HEAD:VERSION 2>$null | Out-String).Trim()
        $ErrorActionPreference = 'Stop'

        if ([string]::IsNullOrWhiteSpace($commitCible) -or $commitCible -eq $commitAvant -or -not (Test-VersionSuperieure -Cible $versionCible -Actuelle $versionAvant)) {
            $donnees['statut'] = 'AUCUNE_MAJ'
            $donnees['version_cible'] = $versionAvant
            $donnees['fin_le'] = (Get-Date).ToString('o')
            $donnees['message'] = "Il n'y a pas de mise à jour disponible (version actuelle : $versionAvant)."
            Save-DemandeAtomique $donnees
            return 0
        }

        $donnees['version_cible'] = $versionCible
        $donnees['statut'] = 'EN_COURS'
        $donnees['debut_le'] = (Get-Date).ToString('o')
        $donnees['message'] = "Nouvelle version $versionCible disponible : sauvegarde chiffrée, reconstruction et redémarrage en cours..."
        Save-DemandeAtomique $donnees

        $ErrorActionPreference = 'Continue'
        & powershell.exe -NoProfile -NonInteractive -ExecutionPolicy Bypass -File $UpdateScript *> $null
        $code = $LASTEXITCODE
        $ErrorActionPreference = 'Stop'

        if ($code -eq 0) {
            $donnees['statut'] = 'TERMINEE'
            $donnees['fin_le'] = (Get-Date).ToString('o')
            $donnees['message'] = "Mise à jour en ligne vers $versionCible appliquée avec succès."
            Save-DemandeAtomique $donnees
            return 0
        }

        $donnees['statut'] = 'ECHEC'
        $donnees['fin_le'] = (Get-Date).ToString('o')
        $donnees['message'] = Get-DerniereErreurJournal
        Save-DemandeAtomique $donnees
        return 1
    }

    # Mode ARCHIVE (.zip déposé par l'application web)
    $nomArchive = [string]$donnees['archive']
    $empreinte = ([string]$donnees['empreinte']).Trim().ToLower()

    if ($nomArchive -notmatch '^yelen-school-\d+\.\d+\.\d+\.bundle$' -or $empreinte -notmatch '^[0-9a-f]{64}$') {
        $donnees['statut'] = 'ECHEC'
        $donnees['fin_le'] = (Get-Date).ToString('o')
        $donnees['message'] = 'Demande de mise à jour invalide (nom de bundle ou empreinte SHA-256 non conforme).'
        Save-DemandeAtomique $donnees
        return 1
    }

    $cheminArchive = Join-Path $UpdateDir $nomArchive
    if (-not (Test-Path -LiteralPath $cheminArchive)) {
        $donnees['statut'] = 'ECHEC'
        $donnees['fin_le'] = (Get-Date).ToString('o')
        $donnees['message'] = "Archive introuvable dans mises-a-jour : $nomArchive"
        Save-DemandeAtomique $donnees
        return 1
    }

    $donnees['statut'] = 'EN_COURS'
    $donnees['debut_le'] = (Get-Date).ToString('o')
    $donnees['message'] = 'Sauvegarde chiffrée, reconstruction et redémarrage en cours sur le serveur...'
    Save-DemandeAtomique $donnees

    $ErrorActionPreference = 'Continue'
    & powershell.exe -NoProfile -NonInteractive -ExecutionPolicy Bypass `
        -File $UpdateScript -DepuisArchive $cheminArchive -Empreinte $empreinte *> $null
    $code = $LASTEXITCODE
    $ErrorActionPreference = 'Stop'

    if ($code -eq 0) {
        Remove-Item -LiteralPath $cheminArchive, "$cheminArchive.sha256" -Force -ErrorAction SilentlyContinue
        $donnees['statut'] = 'TERMINEE'
        $donnees['fin_le'] = (Get-Date).ToString('o')
        $donnees['message'] = "Mise à jour vers $($donnees['version_cible']) appliquée avec succès."
        Save-DemandeAtomique $donnees
        return 0
    }

    $donnees['statut'] = 'ECHEC'
    $donnees['fin_le'] = (Get-Date).ToString('o')
    $donnees['message'] = Get-DerniereErreurJournal
    Save-DemandeAtomique $donnees
    return 1
}

Initialize-HostEnvironment

$passes = if ($UnePasse) { 1 } else { 18 }
for ($i = 0; $i -lt $passes; $i++) {
    $resultat = Invoke-TraitementDemande
    if ($null -ne $resultat) { exit $resultat }
    if ($i -lt ($passes - 1)) { Start-Sleep -Seconds 3 }
}
exit 0
