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
$UpdateDir = Join-Path $Root 'mises-a-jour'
$DemandeFile = Join-Path $UpdateDir 'demande.json'
$UpdateScript = Join-Path $PSScriptRoot 'mettre-a-jour.ps1'
$UpdateLog = Join-Path $Root 'logs\mise-a-jour.log'

function Save-DemandeAtomique {
    param([hashtable]$Donnees)
    $tmp = Join-Path $UpdateDir ".demande.$PID.tmp"
    $json = $Donnees | ConvertTo-Json -Depth 4
    [System.IO.File]::WriteAllText($tmp, "$json`n", (New-Object System.Text.UTF8Encoding($false)))
    Move-Item -LiteralPath $tmp -Destination $DemandeFile -Force
}

function Get-DerniereErreurJournal {
    $defaut = 'La mise à jour a échoué (consulter logs\mise-a-jour.log).'
    if (Test-Path -LiteralPath $UpdateLog) {
        $derniereLigne = Get-Content -LiteralPath $UpdateLog -Tail 15 |
            Where-Object { $_ -match 'ERREUR' } | Select-Object -Last 1
        if ($derniereLigne) { return $derniereLigne }
    }
    return $defaut
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
        $ErrorActionPreference = 'Continue'
        & git -C $Root fetch --quiet origin main *> $null
        $fetchCode = $LASTEXITCODE
        $ErrorActionPreference = 'Stop'

        if ($fetchCode -ne 0) {
            $donnees['statut'] = 'ECHEC'
            $donnees['fin_le'] = (Get-Date).ToString('o')
            $donnees['message'] = 'Dépôt GitHub injoignable : vérifiez la connexion Internet ou utilisez le bouton Mise à jour (.zip).'
            Save-DemandeAtomique $donnees
            return 1
        }

        $commitAvant = (& git -C $Root rev-parse HEAD 2>$null | Out-String).Trim()
        $commitCible = (& git -C $Root rev-parse FETCH_HEAD 2>$null | Out-String).Trim()
        $versionAvant = (& git -C $Root show HEAD:VERSION 2>$null | Out-String).Trim()
        $versionCible = (& git -C $Root show FETCH_HEAD:VERSION 2>$null | Out-String).Trim()

        if ([string]::IsNullOrWhiteSpace($commitCible) -or $commitCible -eq $commitAvant -or $versionCible -eq $versionAvant) {
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

$passes = if ($UnePasse) { 1 } else { 18 }
for ($i = 0; $i -lt $passes; $i++) {
    $resultat = Invoke-TraitementDemande
    if ($null -ne $resultat) { exit $resultat }
    if ($i -lt ($passes - 1)) { Start-Sleep -Seconds 3 }
}
exit 0
