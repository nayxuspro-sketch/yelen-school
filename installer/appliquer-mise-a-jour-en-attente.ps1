#requires -Version 5.1
<##
.SYNOPSIS
    Applique automatiquement une archive de mise à jour déposée depuis Configuration > Mise à jour.
.DESCRIPTION
    Vérifie la présence de mises-a-jour\demande.json avec statut EN_ATTENTE, valide strictement le nom
    du bundle et l'empreinte SHA-256, exécute installer\mettre-a-jour.ps1 -DepuisArchive, puis consigne
    l'état final (TERMINEE ou ECHEC) dans demande.json pour le suivi en direct dans l'interface web.
#>
[CmdletBinding()]
param()

$ErrorActionPreference = 'Stop'
$Root = [System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))
$UpdateDir = Join-Path $Root 'mises-a-jour'
$DemandeFile = Join-Path $UpdateDir 'demande.json'
$UpdateScript = Join-Path $PSScriptRoot 'mettre-a-jour.ps1'
$UpdateLog = Join-Path $Root 'logs\mise-a-jour.log'

if (-not (Test-Path -LiteralPath $DemandeFile)) { exit 0 }

function Save-DemandeAtomique {
    param([hashtable]$Donnees)
    $tmp = Join-Path $UpdateDir ".demande.$PID.tmp"
    $json = $Donnees | ConvertTo-Json -Depth 4
    [System.IO.File]::WriteAllText($tmp, "$json`n", (New-Object System.Text.UTF8Encoding($false)))
    Move-Item -LiteralPath $tmp -Destination $DemandeFile -Force
}

try {
    $brut = [System.IO.File]::ReadAllText($DemandeFile, [System.Text.Encoding]::UTF8)
    $demandeObj = $brut | ConvertFrom-Json
} catch {
    exit 0
}

if ($null -eq $demandeObj -or $demandeObj.statut -ne 'EN_ATTENTE') { exit 0 }

$donnees = @{}
foreach ($prop in $demandeObj.PSObject.Properties) {
    $donnees[$prop.Name] = $prop.Value
}

$nomArchive = [string]$donnees['archive']
$empreinte = ([string]$donnees['empreinte']).Trim().ToLower()

if ($nomArchive -notmatch '^yelen-school-\d+\.\d+\.\d+\.bundle$' -or $empreinte -notmatch '^[0-9a-f]{64}$') {
    $donnees['statut'] = 'ECHEC'
    $donnees['fin_le'] = (Get-Date).ToString('o')
    $donnees['message'] = 'Demande de mise à jour invalide (nom de bundle ou empreinte SHA-256 non conforme).'
    Save-DemandeAtomique $donnees
    exit 1
}

$cheminArchive = Join-Path $UpdateDir $nomArchive
if (-not (Test-Path -LiteralPath $cheminArchive)) {
    $donnees['statut'] = 'ECHEC'
    $donnees['fin_le'] = (Get-Date).ToString('o')
    $donnees['message'] = "Archive introuvable dans mises-a-jour : $nomArchive"
    Save-DemandeAtomique $donnees
    exit 1
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
    exit 0
}

$detailErreur = 'La mise à jour a échoué (consulter logs\mise-a-jour.log).'
if (Test-Path -LiteralPath $UpdateLog) {
    $derniereLigne = Get-Content -LiteralPath $UpdateLog -Tail 15 |
        Where-Object { $_ -match 'ERREUR' } | Select-Object -Last 1
    if ($derniereLigne) { $detailErreur = $derniereLigne }
}
$donnees['statut'] = 'ECHEC'
$donnees['fin_le'] = (Get-Date).ToString('o')
$donnees['message'] = $detailErreur
Save-DemandeAtomique $donnees
exit 1
