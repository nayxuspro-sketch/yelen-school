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
$FirewallScript = Join-Path $PSScriptRoot 'configure-firewall.ps1'
$EnvFile = Join-Path $Root '.env'

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

function Ensure-EnvListValues {
    param(
        [string]$Name,
        [string[]]$RequiredValues
    )

    $current = Get-EnvValue $Name
    if ([string]::IsNullOrWhiteSpace($current) -or $current -match 'generer|choisissez|votre-|changez') {
        $values = @()
    } else {
        $values = @($current -split ',' | ForEach-Object { $_.Trim() } | Where-Object { $_ })
    }
    foreach ($required in $RequiredValues) {
        if ($values -notcontains $required) {
            $values += $required
        }
    }
    Set-EnvValue $Name ($values -join ',')
}

function Test-TcpPortAvailable {
    param([int]$Port)

    $listener = $null
    try {
        $listener = New-Object -TypeName System.Net.Sockets.TcpListener -ArgumentList @(
            [System.Net.IPAddress]::Loopback,
            $Port
        )
        $listener.Start()
        return $true
    } catch {
        return $false
    } finally {
        if ($null -ne $listener) {
            try { $listener.Stop() } catch { }
        }
    }
}

function Test-YelenPortInUse {
    param([int]$Port)

    $published = @()
    $composeExitCode = 1
    Push-Location $Root
    try {
        # Le port 8000 est le port interne du conteneur web. Docker Compose
        # renvoie ici le port publié réellement utilisé par YELEN SCHOOL.
        $published = @(& docker compose -f $ComposeFile port web 8000 2>$null)
        $composeExitCode = $LASTEXITCODE
    } catch {
        return $false
    } finally {
        Pop-Location
    }

    if ($composeExitCode -ne 0) {
        return $false
    }

    return [bool]($published | Where-Object {
        $_.ToString().Trim() -match "(^|:)$Port$"
    })
}

function Select-HttpPort {
    param([int]$PreferredPort)

    # L'ordre de repli est volontairement limité aux ports documentés pour
    # éviter de choisir un port inattendu chez le client.
    $candidatePorts = @($PreferredPort) + @(8000..8005)
    $candidatePorts = @($candidatePorts | Select-Object -Unique)

    foreach ($candidate in $candidatePorts) {
        # Si YELEN SCHOOL tourne déjà sur ce port, le conserver lors d'un
        # nouveau lancement de demarrage.bat.
        if (Test-YelenPortInUse $candidate) {
            return [int]$candidate
        }
        if (Test-TcpPortAvailable $candidate) {
            return [int]$candidate
        }
    }

    throw 'Aucun port disponible dans la plage YELEN SCHOOL (8000 à 8005). Libérez un port ou définissez un autre YELEN_HTTP_PORT dans .env.'
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

$httpPort = Get-EnvValue 'YELEN_HTTP_PORT'
if ([string]::IsNullOrWhiteSpace($httpPort)) {
    $httpPort = '8000'
}
$requestedHttpPortNumber = 0
if (-not [int]::TryParse($httpPort, [ref]$requestedHttpPortNumber) -or $requestedHttpPortNumber -lt 1 -or $requestedHttpPortNumber -gt 65535) {
    Stop-Installation 'YELEN_HTTP_PORT doit être un port compris entre 1 et 65535.'
}

try {
    $httpPortNumber = Select-HttpPort $requestedHttpPortNumber
} catch {
    Stop-Installation $_.Exception.Message
}
$httpPort = [string]$httpPortNumber
if ($httpPortNumber -ne $requestedHttpPortNumber) {
    Write-Host "[AVERTISSEMENT] Le port TCP $requestedHttpPortNumber est déjà utilisé. Port sélectionné automatiquement : $httpPortNumber." -ForegroundColor Yellow
    Set-EnvValue 'YELEN_HTTP_PORT' $httpPort
} else {
    Write-Host "[OK] Port HTTP sélectionné : $httpPort" -ForegroundColor Green
}
$LoginUrl = "http://localhost:$httpPort/accounts/login/"

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
Ensure-EnvListValues 'CSRF_TRUSTED_ORIGINS' @(
    'http://localhost',
    'http://127.0.0.1',
    "http://localhost:$httpPort",
    "http://127.0.0.1:$httpPort",
    "http://${lanIp}:$httpPort"
)
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

if (Test-Path $FirewallScript) {
    Write-Host '[OK] Configuration du pare-feu Windows pour le réseau local...' -ForegroundColor Cyan
    & powershell.exe -NoProfile -ExecutionPolicy Bypass -File $FirewallScript -Port $httpPortNumber
    if ($LASTEXITCODE -ne 0) {
        Write-Host '[AVERTISSEMENT] Le pare-feu n’a pas été configuré. L’application restera accessible localement, mais l’accès depuis les autres postes peut être bloqué.' -ForegroundColor Yellow
        Write-Host 'Relancez demarrage.bat et acceptez la demande UAC pour autoriser le réseau local.' -ForegroundColor Yellow
    }
} else {
    Write-Host '[AVERTISSEMENT] Script de configuration du pare-feu introuvable : accès réseau local non configuré.' -ForegroundColor Yellow
}

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
Write-Host "Accès réseau local : http://${lanIp}:$httpPort/" -ForegroundColor White

if (-not $NoBrowser) {
    Start-Process $LoginUrl
}
