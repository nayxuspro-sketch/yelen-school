#requires -Version 5.1
<##
.SYNOPSIS
    Active (ou désactive) le HTTPS de YELEN SCHOOL sur le réseau local.

.DESCRIPTION
    À exécuter en administrateur (activer-https.bat). Le script :
      1. génère dans certs\ une autorité locale et un certificat serveur couvrant les
         adresses IP et le nom du serveur (installer\generer-certificats.py, dans le conteneur web) ;
      2. inscrit dans .env : YELEN_HTTPS=true, YELEN_HTTPS_PORT, YELEN_HTTPS_HOSTS,
         COMPOSE_PROFILES=https et YELEN_WEB_BIND=127.0.0.1 (HTTP fermé sur le réseau,
         conservé sur le serveur pour la surveillance) ;
      3. ouvre le port HTTPS dans le pare-feu, installe l'autorité sur ce serveur,
         redémarre les services et vérifie https://127.0.0.1:<port>/health/.
    Ensuite, start-local.ps1 (démarrage et surveillance) renouvelle seul le certificat
    après un changement d'adresse IP ou de nom, et avant son expiration (autorité
    conservée : rien à refaire sur les postes). Relancer ce script uniquement pour
    forcer un renouvellement, imposer la liste d'adresses (-Hosts) ou changer de port.

.EXAMPLE
    .\installer\activer-https.ps1
    .\installer\activer-https.ps1 -Hosts 192.168.1.10,serveur-ecole -Port 8443
    .\installer\activer-https.ps1 -Desactiver
#>
[CmdletBinding()]
param(
    [string[]]$Hosts = @(),
    [ValidateRange(1, 65535)]
    [int]$Port = 8443,
    [switch]$Desactiver
)

$ErrorActionPreference = 'Stop'
$Root = [System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))
$ComposeFile = Join-Path $Root 'docker-compose.client.yml'
$EnvFile = Join-Path $Root '.env'
$StartScript = Join-Path $PSScriptRoot 'start-local.ps1'
$CertDirectory = Join-Path $Root 'certs'
$CaFile = Join-Path $CertDirectory 'yelen-ca.crt'
$RuleName = 'YELEN_SCHOOL_LocalHttps'

function Get-DotEnvValue {
    param([string]$Name)
    $line = Get-Content $EnvFile | Where-Object { $_ -match "^$([regex]::Escape($Name))=" } | Select-Object -First 1
    if ($null -eq $line) { return '' }
    return ($line -replace "^$([regex]::Escape($Name))=", '').Trim()
}

function Set-DotEnvValue {
    param([string]$Name, [string]$Value)
    $content = [System.IO.File]::ReadAllText($EnvFile, [System.Text.UTF8Encoding]::new($false))
    $pattern = "(?m)^$([regex]::Escape($Name))=.*$"
    $line = "$Name=$Value"
    if ([regex]::IsMatch($content, $pattern)) {
        $content = [regex]::Replace($content, $pattern, [System.Text.RegularExpressions.MatchEvaluator]{ param($match) $line })
    } else {
        $separator = if ($content.EndsWith("`n")) { '' } else { "`r`n" }
        $content = "$content$separator$line`r`n"
    }
    # UTF-8 sans BOM : un BOM rendrait la première clé du .env illisible pour Docker Compose.
    [System.IO.File]::WriteAllText($EnvFile, $content, [System.Text.UTF8Encoding]::new($false))
}

function Invoke-Start {
    & powershell.exe -NoProfile -ExecutionPolicy Bypass -File $StartScript
    if ($LASTEXITCODE -ne 0) { throw 'Le redémarrage des services a échoué (voir logs\startup.log).' }
}

$principal = New-Object Security.Principal.WindowsPrincipal([Security.Principal.WindowsIdentity]::GetCurrent())
if (-not $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    throw 'Ce script doit être exécuté en tant qu''administrateur (pare-feu et autorité de certification).'
}
if (-not (Test-Path $EnvFile)) { throw '.env est introuvable. Lancez d''abord l''installation locale.' }
if (-not (Get-Command docker -ErrorAction SilentlyContinue)) { throw 'Docker est introuvable.' }
& docker info *> $null
if ($LASTEXITCODE -ne 0) { throw 'Docker ne fonctionne pas.' }

if ($Desactiver) {
    Write-Host '[1/3] Désactivation du HTTPS dans .env...' -ForegroundColor Cyan
    Set-DotEnvValue 'YELEN_HTTPS' 'false'
    Set-DotEnvValue 'COMPOSE_PROFILES' ''
    Set-DotEnvValue 'YELEN_WEB_BIND' '0.0.0.0'
    Write-Host '[2/3] Arrêt du proxy et fermeture du port dans le pare-feu...' -ForegroundColor Cyan
    & docker compose -f $ComposeFile --profile https rm -sf proxy *> $null
    Get-NetFirewallRule -Name $RuleName -ErrorAction SilentlyContinue | Remove-NetFirewallRule
    Write-Host '[3/3] Redémarrage des services...' -ForegroundColor Cyan
    Invoke-Start
    $httpPort = Get-DotEnvValue 'YELEN_HTTP_PORT'
    Write-Host "[OK] HTTPS désactivé. L'application répond de nouveau en HTTP sur le port $httpPort." -ForegroundColor Green
    exit 0
}

# ── 1. Adresses couvertes par le certificat ────────────────────────────────
if ($Hosts.Count -eq 0) {
    $memo = Get-DotEnvValue 'YELEN_HTTPS_HOSTS'
    $lan = @(Get-NetIPAddress -AddressFamily IPv4 -ErrorAction SilentlyContinue |
        Where-Object { $_.IPAddress -notlike '127.*' -and $_.IPAddress -notlike '169.254.*' -and
                       $_.InterfaceAlias -notlike 'vEthernet*' -and $_.InterfaceAlias -notlike '*Loopback*' } |
        Select-Object -ExpandProperty IPAddress)
    # NOMPC (postes Windows) et NOMPC.local (tablettes, téléphones, Mac) : cf. §9.1 du guide.
    $Hosts = @($lan) + @($env:COMPUTERNAME, "$env:COMPUTERNAME.local") + @($memo -split '[,; ]+')
}
$Hosts = @(@($Hosts) + @('localhost', '127.0.0.1') | ForEach-Object { "$_".Trim() } | Where-Object { $_ } | Select-Object -Unique)
$hostList = $Hosts -join ','

# ── 2. Port HTTPS libre ? ──────────────────────────────────────────────────
$proxyRunning = (& docker compose -f $ComposeFile --profile https ps -q --status running proxy 2>$null)
if (-not $proxyRunning -and (Get-NetTCPConnection -State Listen -LocalPort $Port -ErrorAction SilentlyContinue)) {
    throw "Le port TCP $Port est déjà utilisé. Relancez avec -Port <autre port>."
}

# ── 3. Certificats ─────────────────────────────────────────────────────────
Write-Host "[1/5] Génération des certificats pour : $hostList" -ForegroundColor Cyan
New-Item -ItemType Directory -Path $CertDirectory -Force | Out-Null
& docker compose -f $ComposeFile run --rm --no-deps --entrypoint python web /app/installer/generer-certificats.py --hosts $hostList --out /app/certs
if ($LASTEXITCODE -ne 0 -or -not (Test-Path $CaFile)) { throw 'La génération des certificats a échoué.' }

# ── 4. Configuration ───────────────────────────────────────────────────────
Write-Host '[2/5] Mise à jour de .env (YELEN_HTTPS, COMPOSE_PROFILES, YELEN_WEB_BIND)...' -ForegroundColor Cyan
Set-DotEnvValue 'YELEN_HTTPS' 'true'
Set-DotEnvValue 'YELEN_HTTPS_PORT' ([string]$Port)
Set-DotEnvValue 'YELEN_HTTPS_HOSTS' $hostList
Set-DotEnvValue 'COMPOSE_PROFILES' 'https'
Set-DotEnvValue 'YELEN_WEB_BIND' '127.0.0.1'

Write-Host "[3/5] Pare-feu : TCP $Port autorisé sur le réseau privé ; autorité installée sur ce serveur..." -ForegroundColor Cyan
Get-NetFirewallRule -Name $RuleName -ErrorAction SilentlyContinue | Remove-NetFirewallRule
New-NetFirewallRule -Name $RuleName -DisplayName 'YELEN SCHOOL - Accès réseau local (HTTPS)' -Group 'YELEN SCHOOL' `
    -Description "Autorise YELEN SCHOOL en HTTPS sur le port TCP $Port depuis le réseau local." `
    -Direction Inbound -Action Allow -Protocol TCP -LocalPort $Port -Profile Private, Domain `
    -RemoteAddress LocalSubnet -Enabled True -EdgeTraversalPolicy Block | Out-Null
Import-Certificate -FilePath $CaFile -CertStoreLocation Cert:\LocalMachine\Root | Out-Null

# ── 5. Redémarrage et contrôle ─────────────────────────────────────────────
Write-Host '[4/5] Redémarrage des services avec le proxy HTTPS...' -ForegroundColor Cyan
Invoke-Start

Write-Host "[5/5] Contrôle de https://127.0.0.1:$Port/health/ ..." -ForegroundColor Cyan
$ok = $false
for ($i = 0; $i -lt 30 -and -not $ok; $i++) {
    try {
        $ok = (Invoke-WebRequest -Uri "https://127.0.0.1:$Port/health/" -UseBasicParsing -TimeoutSec 10).StatusCode -eq 200
    } catch { Start-Sleep -Seconds 3 }
}
if (-not $ok) { throw "Le proxy HTTPS ne répond pas. Consultez : docker compose -f docker-compose.client.yml logs proxy" }

$ip = ($Hosts | Where-Object { $_ -match '^\d+\.\d+\.\d+\.\d+$' -and $_ -ne '127.0.0.1' } | Select-Object -First 1)
Write-Host ''
Write-Host "[OK] HTTPS actif : https://${ip}:$Port/" -ForegroundColor Green
Write-Host "     L'accès HTTP n'est plus ouvert sur le réseau (conservé sur le serveur : http://127.0.0.1:$(Get-DotEnvValue 'YELEN_HTTP_PORT')/)."
Write-Host ''
Write-Host 'Sur chaque poste : copier certs\yelen-ca.crt et installer\installer-certificat-poste.bat dans un même dossier,' -ForegroundColor Yellow
Write-Host 'puis exécuter le .bat en tant qu''administrateur (une seule fois par poste).' -ForegroundColor Yellow
