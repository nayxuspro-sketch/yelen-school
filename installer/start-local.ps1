#requires -Version 5.1
<##
.SYNOPSIS
    Démarre les services locaux YELEN SCHOOL après l'ouverture de session Windows.
#>

[CmdletBinding()]
param(
    [switch]$OpenBrowser
)

$ErrorActionPreference = 'Stop'
$Root = [System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))
$ComposeFile = Join-Path $Root 'docker-compose.client.yml'
$EnvFile = Join-Path $Root '.env'
$LogDirectory = Join-Path $Root 'logs'
$LogFile = Join-Path $LogDirectory 'startup.log'

function Write-StartupLog {
    param([string]$Message)
    $line = "$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') $Message"
    Add-Content -Path $LogFile -Value $line -Encoding UTF8
    Write-Host $line
}

function Get-DotEnvValue {
    param([string]$Name)
    if (-not (Test-Path $EnvFile)) { return '' }
    $line = Get-Content $EnvFile | Where-Object { $_ -match "^$([regex]::Escape($Name))=" } | Select-Object -First 1
    if ($null -eq $line) { return '' }
    return ($line -replace "^$([regex]::Escape($Name))=", '').Trim()
}

New-Item -ItemType Directory -Path $LogDirectory -Force | Out-Null
try {
    if (-not (Test-Path $ComposeFile)) {
        throw "Fichier introuvable : $ComposeFile"
    }
    if (-not (Test-Path $EnvFile)) {
        throw '.env est introuvable. Exécutez demarrage.bat une première fois.'
    }
    if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
        throw 'Docker est introuvable dans le PATH.'
    }

    & docker info *> $null
    if ($LASTEXITCODE -ne 0) {
        $desktopCandidates = @(
            (Join-Path ${env:ProgramFiles} 'Docker\Docker\Docker Desktop.exe'),
            (Join-Path ${env:LOCALAPPDATA} 'Docker\Docker Desktop.exe')
        )
        $desktopPath = $desktopCandidates | Where-Object { Test-Path $_ } | Select-Object -First 1
        if ($desktopPath -and -not (Get-Process -ErrorAction SilentlyContinue | Where-Object { $_.ProcessName -eq 'Docker Desktop' })) {
            Write-StartupLog 'Démarrage de Docker Desktop...'
            Start-Process -FilePath $desktopPath | Out-Null
        }
    }

    $dockerReady = $false
    for ($attempt = 1; $attempt -le 90; $attempt++) {
        & docker info *> $null
        if ($LASTEXITCODE -eq 0) {
            $dockerReady = $true
            break
        }
        Start-Sleep -Seconds 2
    }
    if (-not $dockerReady) {
        throw 'Docker Desktop ne répond pas après 180 secondes.'
    }

    Set-Location $Root
    Write-StartupLog 'Démarrage des services YELEN SCHOOL...'
    & docker compose -f $ComposeFile up -d
    if ($LASTEXITCODE -ne 0) {
        throw 'Le démarrage Docker Compose a échoué.'
    }
    Write-StartupLog 'Services YELEN SCHOOL démarrés.'

    if ($OpenBrowser) {
        $port = Get-DotEnvValue 'YELEN_HTTP_PORT'
        if ([string]::IsNullOrWhiteSpace($port)) { $port = '8000' }
        Start-Process "http://127.0.0.1:$port/accounts/login/"
    }
} catch {
    Write-StartupLog "ERREUR : $($_.Exception.Message)"
    exit 1
}
