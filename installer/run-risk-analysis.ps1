#requires -Version 5.1
<##
.SYNOPSIS
    Exécute l'analyse quotidienne du risque de décrochage dans Docker.

.DESCRIPTION
    Le script est appelé par la tâche planifiée Windows. Il démarre les services
    sans reconstruire l'image, exécute la commande Django en mode strict et écrit
    le résultat dans logs\risques.log.
#>

[CmdletBinding()]
param(
    [string]$TaskLog = ''
)

$ErrorActionPreference = 'Stop'
$Root = [System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))
$ComposeFile = Join-Path $Root 'docker-compose.client.yml'
$LogDirectory = Join-Path $Root 'logs'
if ([string]::IsNullOrWhiteSpace($TaskLog)) {
    $TaskLog = Join-Path $LogDirectory 'risques.log'
}

function Write-RiskLog {
    param([string]$Message)
    $line = "$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') $Message"
    Add-Content -LiteralPath $TaskLog -Value $line -Encoding UTF8
    Write-Host $line
}

try {
    New-Item -ItemType Directory -Path $LogDirectory -Force | Out-Null
    New-Item -ItemType Directory -Path ([System.IO.Path]::GetDirectoryName($TaskLog)) -Force | Out-Null

    if (-not (Test-Path $ComposeFile)) {
        throw "Fichier Compose introuvable : $ComposeFile"
    }
    if (-not (Test-Path (Join-Path $Root '.env'))) {
        throw '.env est introuvable. Exécutez demarrage.bat avant de programmer l analyse.'
    }
    if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
        throw 'Docker est introuvable dans le PATH.'
    }

    Set-Location $Root
    Write-RiskLog 'Vérification du moteur Docker...'
    & docker info *> $null
    if ($LASTEXITCODE -ne 0) {
        throw 'Docker Desktop ne répond pas. Démarrez Docker Desktop puis relancez la tâche.'
    }

    Write-RiskLog 'Démarrage des services YELEN SCHOOL sans reconstruction...'
    & docker compose -f $ComposeFile up -d 2>&1 | ForEach-Object {
        Add-Content -LiteralPath $TaskLog -Value $_ -Encoding UTF8
    }
    if ($LASTEXITCODE -ne 0) {
        throw 'Le démarrage Docker Compose a échoué.'
    }

    Write-RiskLog 'Calcul des risques de décrochage...'
    & docker compose -f $ComposeFile exec -T web python manage.py calculer_risques --strict 2>&1 | ForEach-Object {
        Add-Content -LiteralPath $TaskLog -Value $_ -Encoding UTF8
        Write-Host $_
    }
    if ($LASTEXITCODE -ne 0) {
        throw 'La commande calculer_risques a échoué. Consultez logs\risques.log.'
    }

    Write-RiskLog 'Analyse des risques terminée avec succès.'
    exit 0
} catch {
    try {
        New-Item -ItemType Directory -Path ([System.IO.Path]::GetDirectoryName($TaskLog)) -Force | Out-Null
        Write-RiskLog "ERREUR : $($_.Exception.Message)"
    } catch {
        Write-Error $_.Exception.Message
    }
    exit 1
}
