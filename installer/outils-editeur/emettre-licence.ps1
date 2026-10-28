#requires -Version 5.1
<##
.SYNOPSIS
    Émet un code de licence YELEN3 signé avec la clé privée de l'éditeur.
.DESCRIPTION
    Outil de l'éditeur, à exécuter sur son environnement (poste ou environnement de test), jamais
    sur le serveur d'un client. Lit LICENCE_PRIVATE_KEY dans le fichier des clés (créé par
    installer\creer-environnement-test.ps1 ou par manage.py generate_licence_keys --format env),
    puis exécute manage.py emettre_licence :
      - avec .venv\Scripts\python.exe si ce dossier est une installation autonome (SQLite) ;
      - sinon dans l'image Docker de ce dossier (docker compose run, sans base de données).
    La commande n'écrit rien en base : elle affiche le code YELEN3.… que le Super Admin du client
    colle dans Licences > Activer. La clé privée n'apparaît ni à l'écran ni dans un fichier .env.
.PARAMETER Etablissement
    Identifiant établissement (UUID) relevé sur la page d'activation du client.
.PARAMETER Type
    Niveau de licence : STARTER, STANDARD, PREMIUM ou RESEAU.
.PARAMETER Expiration
    Date de fin de validité (AAAA-MM-JJ).
.PARAMETER Empreinte
    Identifiant du serveur (64 caractères hexadécimaux) relevé sur la page d'activation ; omis = licence non liée.
.PARAMETER Cle
    Clé YELEN-XXXX-XXXX-XXXX à conserver (renouvellement, changement de serveur) ; omise = nouvelle clé.
.PARAMETER Activation
    Date de début de validité (AAAA-MM-JJ) ; omise = aujourd'hui.
.PARAMETER FichierCles
    Fichier des clés de l'éditeur (défaut : <dossier parent de l'installation>\YELEN-EDITEUR\cles-editeur.txt).
.EXAMPLE
    powershell -NoProfile -ExecutionPolicy Bypass -File installer\outils-editeur\emettre-licence.ps1 -Etablissement 3f2a… -Type STARTER -Expiration 2027-08-31 -Empreinte 9c1e…
#>

[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string]$Etablissement,
    [Parameter(Mandatory = $true)]
    [ValidateSet('STARTER', 'STANDARD', 'PREMIUM', 'RESEAU')]
    [string]$Type,
    [Parameter(Mandatory = $true)]
    [string]$Expiration,
    [string]$Empreinte = '',
    [string]$Cle = '',
    [string]$Activation = '',
    [string]$FichierCles = ''
)

$ErrorActionPreference = 'Stop'
$Root = [System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..\..'))
if ([string]::IsNullOrWhiteSpace($FichierCles)) {
    $FichierCles = Join-Path (Split-Path $Root -Parent) 'YELEN-EDITEUR\cles-editeur.txt'
}

function Get-DotEnvLines {
    # Lignes NOM=valeur du .env de l'installation autonome (commentaires et lignes vides ignorés).
    param([string]$Path)
    if (-not (Test-Path $Path)) { return @() }
    return @(Get-Content $Path | Where-Object { $_ -match '^\s*[A-Za-z_][A-Za-z0-9_]*\s*=' })
}

try {
    if (-not (Test-Path $FichierCles)) {
        throw "Fichier des clés introuvable : $FichierCles (créé par creer-environnement-test.bat ; sinon indiquer -FichierCles)."
    }
    $ligneCle = Get-Content $FichierCles | Where-Object { $_ -match '^LICENCE_PRIVATE_KEY=[0-9A-Fa-f]+\s*$' } | Select-Object -First 1
    if ($null -eq $ligneCle) { throw "Aucune ligne LICENCE_PRIVATE_KEY=… valide dans $FichierCles." }
    $clePrivee = ($ligneCle -replace '^LICENCE_PRIVATE_KEY=', '').Trim()

    $arguments = @('manage.py', 'emettre_licence', '--etablissement', $Etablissement, '--type', $Type, '--expiration', $Expiration)
    if ($Empreinte) { $arguments += @('--empreinte', $Empreinte) }
    if ($Cle) { $arguments += @('--cle', $Cle) }
    if ($Activation) { $arguments += @('--activation', $Activation) }

    $ErrorActionPreference = 'Continue'
    $python = Join-Path $Root '.venv\Scripts\python.exe'
    if (Test-Path $python) {
        # Installation autonome : variables du .env puis clé privée, pour ce processus seulement.
        foreach ($ligne in Get-DotEnvLines (Join-Path $Root '.env')) {
            $nom, $valeur = $ligne -split '=', 2
            [System.Environment]::SetEnvironmentVariable($nom.Trim(), $valeur.Trim(), 'Process')
        }
        $env:LICENCE_PRIVATE_KEY = $clePrivee
        Push-Location $Root
        try { & $python @arguments } finally { Pop-Location }
    } else {
        $composeFile = Join-Path $Root 'docker-compose.client.yml'
        if (-not (Test-Path $composeFile) -or -not (Test-Path (Join-Path $Root '.env'))) {
            throw "Ni .venv\Scripts\python.exe ni installation Docker (.env) dans $Root."
        }
        & docker compose -f $composeFile run --rm --no-deps -T -e "LICENCE_PRIVATE_KEY=$clePrivee" --entrypoint python web @arguments
    }
    exit $LASTEXITCODE
} catch {
    Write-Host "ERREUR : $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}
