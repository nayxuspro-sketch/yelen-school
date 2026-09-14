#requires -Version 5.1
<##
.SYNOPSIS
    Installe et démarre YELEN SCHOOL en local sous Windows.

.DESCRIPTION
    Prépare le fichier .env, lance PostgreSQL, Redis et YELEN SCHOOL via
    Docker, puis ouvre la page de connexion. Les données restent dans des
    volumes Docker persistants.
#>

[CmdletBinding()]
param(
    [switch]$NoBrowser
)

$ErrorActionPreference = 'Stop'
$Root = [System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))
$ComposeFile = Join-Path $Root 'docker-compose.client.yml'
$EnvFile = Join-Path $Root '.env'
$LoginUrl = 'http://localhost:8000/accounts/login/'

function Stop-Installation {
    param([string]$Message)
    Write-Host "[ERREUR] $Message" -ForegroundColor Red
    exit 1
}

function Get-EnvValue {
    param([string]$Name)

    $escapedName = [regex]::Escape($Name)
    $match = [regex]::Match($script:EnvContent, "(?m)^$escapedName=(.*)$")
    if ($match.Success) {
        return $match.Groups[1].Value.Trim()
    }
    return ''
}

function Set-EnvValue {
    param(
        [string]$Name,
        [string]$Value
    )

    $escapedName = [regex]::Escape($Name)
    $line = "$Name=$Value"
    if ([regex]::IsMatch($script:EnvContent, "(?m)^$escapedName=.*$")) {
        # Les valeurs générées par ce script ne contiennent pas de caractères
        # spéciaux d'expression régulière dans la chaîne de remplacement.
        $script:EnvContent = [regex]::Replace(
            $script:EnvContent,
            "(?m)^$escapedName=.*$",
            [System.Text.RegularExpressions.MatchEvaluator]{ param($match) $line }
        )
    } else {
        $separator = if ($script:EnvContent.EndsWith("`n")) { '' } else { "`r`n" }
        $script:EnvContent = "$script:EnvContent$separator$line`r`n"
    }
}

function Ensure-EnvValue {
    param(
        [string]$Name,
        [string]$Value
    )

    $current = Get-EnvValue $Name
    if ([string]::IsNullOrWhiteSpace($current) -or $current -match 'generer|choisissez|votre-|changez') {
        Set-EnvValue $Name $Value
    }
}

Write-Host '>>> YELEN SCHOOL - Installation locale' -ForegroundColor Cyan
Write-Host ''

if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
    Stop-Installation 'Docker est introuvable. Installez Docker Desktop puis relancez ce script.'
}

& docker info *> $null
if ($LASTEXITCODE -ne 0) {
    Stop-Installation 'Docker Desktop ne fonctionne pas. Démarrez Docker Desktop puis relancez ce script.'
}

if (-not (Test-Path $ComposeFile)) {
    Stop-Installation "Fichier introuvable : $ComposeFile"
}

$FreshInstallation = -not (Test-Path $EnvFile)
if ($FreshInstallation) {
    $ExampleFile = Join-Path $Root '.env.example'
    if (-not (Test-Path $ExampleFile)) {
        Stop-Installation 'Le fichier .env.example est introuvable.'
    }
    Copy-Item $ExampleFile $EnvFile
    Write-Host '[OK] Fichier .env créé à partir de .env.example' -ForegroundColor Green
}

$script:EnvContent = Get-Content $EnvFile -Raw
if ($null -eq $script:EnvContent) {
    $script:EnvContent = ''
}

$secretKey = ([guid]::NewGuid().ToString('N') + [guid]::NewGuid().ToString('N'))
$dbPassword = 'Yelen-' + [guid]::NewGuid().ToString('N')

$lanIp = Get-NetIPAddress -AddressFamily IPv4 -PrefixOrigin Dhcp -ErrorAction SilentlyContinue |
    Where-Object {
        $_.IPAddress -notlike '127.*' -and
        $_.IPAddress -notlike '169.254.*'
    } |
    Select-Object -First 1 -ExpandProperty IPAddress

if ([string]::IsNullOrWhiteSpace($lanIp)) {
    $lanIp = '127.0.0.1'
}

Ensure-EnvValue 'SECRET_KEY' $secretKey
if ($FreshInstallation) {
    Ensure-EnvValue 'DB_PASSWORD' $dbPassword
} else {
    $existingDbPassword = Get-EnvValue 'DB_PASSWORD'
    if ([string]::IsNullOrWhiteSpace($existingDbPassword) -or $existingDbPassword -match 'generer|choisissez|votre-|changez') {
        Stop-Installation 'DB_PASSWORD doit être configuré dans .env avant de réutiliser une base existante.'
    }
}
Ensure-EnvValue 'DB_NAME' 'yelen_school_db'
Ensure-EnvValue 'DB_USER' 'yelen_user'
Ensure-EnvValue 'DEBUG' 'False'
Ensure-EnvValue 'DISABLE_HTTPS_REDIRECT' 'true'
Ensure-EnvValue 'ALLOWED_HOSTS' "localhost,127.0.0.1,$lanIp"
Ensure-EnvValue 'CSRF_TRUSTED_ORIGINS' "http://localhost,http://127.0.0.1,http://${lanIp}:8000"
if ($FreshInstallation) {
    Set-EnvValue 'ENSURE_ADMIN' 'true'
    # L'installation locale ne doit pas dépendre d'un serveur SMTP externe.
    Set-EnvValue 'EMAIL_HOST' ''
}

[System.IO.File]::WriteAllText(
    $EnvFile,
    $script:EnvContent,
    [System.Text.UTF8Encoding]::new($false)
)
Write-Host '[OK] Configuration locale préparée' -ForegroundColor Green

Set-Location $Root
Write-Host '[1/3] Construction et démarrage des services...' -ForegroundColor Cyan
& docker compose -f $ComposeFile up -d --build
if ($LASTEXITCODE -ne 0) {
    Stop-Installation 'Le démarrage Docker a échoué. Consultez les logs avec : docker compose -f docker-compose.client.yml logs'
}

Write-Host '[2/3] Attente de la page de connexion...' -ForegroundColor Cyan
$ready = $false
for ($attempt = 1; $attempt -le 60; $attempt++) {
    try {
        $response = Invoke-WebRequest -Uri $LoginUrl -UseBasicParsing -TimeoutSec 3
        if ($response.StatusCode -in @(200, 301, 302, 403)) {
            $ready = $true
            break
        }
    } catch {
        # Le conteneur peut prendre quelques secondes pour appliquer les migrations.
    }
    Start-Sleep -Seconds 2
}

if (-not $ready) {
    Write-Host ''
    & docker compose -f $ComposeFile logs --tail=80 web
    Stop-Installation 'Le serveur ne répond pas après 120 secondes.'
}

if ($FreshInstallation) {
    # Le compte initial a été créé par entrypoint.sh. On évite de réinitialiser
    # son mot de passe lors des prochains redémarrages.
    $script:EnvContent = Get-Content $EnvFile -Raw
    Set-EnvValue 'ENSURE_ADMIN' 'false'
    [System.IO.File]::WriteAllText(
        $EnvFile,
        $script:EnvContent,
        [System.Text.UTF8Encoding]::new($false)
    )
}

Write-Host '[OK] YELEN SCHOOL est opérationnel' -ForegroundColor Green
Write-Host ''
Write-Host "Adresse : $LoginUrl" -ForegroundColor White
if ($FreshInstallation) {
    Write-Host 'Compte initial :' -ForegroundColor Yellow
    Write-Host '  Email       : admin@yelen.edu' -ForegroundColor Yellow
    Write-Host '  Mot de passe: admin123' -ForegroundColor Yellow
    Write-Host 'Changez ce mot de passe après la première connexion.' -ForegroundColor Yellow
}
Write-Host "Accès réseau local : http://${lanIp}:8000/" -ForegroundColor White

if (-not $NoBrowser) {
    Start-Process $LoginUrl
}
