#requires -Version 5.1
<##
.SYNOPSIS
    Surveille YELEN SCHOOL : point de santé, redémarrage automatique, alerte SMS.

.DESCRIPTION
    Exécuté toutes les 5 minutes par la tâche planifiée (register-watchdog-task.ps1) :
      1. interroge http://127.0.0.1:<YELEN_HTTP_PORT>/health/ (base + cache) ;
      2. après deux échecs consécutifs, relance les services (start-local.ps1) ;
      3. si l'application reste indisponible, envoie UN SMS d'alerte aux numéros
         ALERTE_SMS_NUMEROS du .env via la passerelle SMS déjà configurée
         (SMS_HTTP_URL / SMS_HTTP_USER / SMS_HTTP_PASSWORD), puis un SMS de retour
         à la normale ;
      4. signale (un SMS par jour) l'absence de sauvegarde depuis plus de 36 heures ;
      5. détecte une nouvelle adresse IP du serveur (nouveau réseau, nouvelle box) et
         relance start-local.ps1, qui autorise l'adresse et renouvelle le certificat HTTPS.
    État conservé dans logs\surveillance.json, journal dans logs\surveillance.log.
#>
[CmdletBinding()]
param(
    [int]$EchecsAvantRedemarrage = 2,
    [int]$HeuresSansSauvegardeMax = 36
)

$ErrorActionPreference = 'Stop'
$Root = [System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))
$EnvFile = Join-Path $Root '.env'
$StartScript = Join-Path $PSScriptRoot 'start-local.ps1'
$LogDirectory = Join-Path $Root 'logs'
$LogFile = Join-Path $LogDirectory 'surveillance.log'
$StateFile = Join-Path $LogDirectory 'surveillance.json'
$BackupDirectory = Join-Path $Root 'backups'

New-Item -ItemType Directory -Path $LogDirectory -Force | Out-Null

function Write-Log {
    param([string]$Message)
    Add-Content -Path $LogFile -Value "$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') $Message" -Encoding UTF8
}

function Invoke-NativeQuiet {
    # Exécute une commande native sans afficher sa sortie et retourne son code de retour.
    # Sous $ErrorActionPreference = 'Stop', Windows PowerShell transforme la sortie
    # d'erreur redirigée d'une commande native en exception (progression de docker
    # compose, avertissements) : elle est ignorée ici.
    param([Parameter(Mandatory = $true)][scriptblock]$Command)
    $ErrorActionPreference = 'Continue'
    & $Command *> $null
    return $LASTEXITCODE
}

function Get-DotEnvValue {
    param([string]$Name)
    if (-not (Test-Path $EnvFile)) { return '' }
    $line = Get-Content $EnvFile | Where-Object { $_ -match "^$([regex]::Escape($Name))=" } | Select-Object -First 1
    if ($null -eq $line) { return '' }
    return ($line -replace "^$([regex]::Escape($Name))=", '').Trim()
}

function Get-Etat {
    if (Test-Path $StateFile) {
        try { return (Get-Content $StateFile -Raw | ConvertFrom-Json) } catch { }
    }
    return [pscustomobject]@{ echecs = 0; alerte_envoyee = $false; alerte_sauvegarde = '' }
}

function Save-Etat {
    param($Etat)
    $Etat | ConvertTo-Json -Compress | Set-Content -Path $StateFile -Encoding UTF8
}

function Test-Sante {
    $port = Get-DotEnvValue 'YELEN_HTTP_PORT'
    if ([string]::IsNullOrWhiteSpace($port)) { $port = '8000' }
    try {
        $reponse = Invoke-WebRequest -Uri "http://127.0.0.1:$port/health/" -UseBasicParsing -TimeoutSec 15
        return ($reponse.StatusCode -eq 200)
    } catch {
        return $false
    }
}

function Send-AlerteSms {
    param([string]$Message)
    $url = Get-DotEnvValue 'SMS_HTTP_URL'
    $numeros = @((Get-DotEnvValue 'ALERTE_SMS_NUMEROS') -split '[,; ]+' | Where-Object { $_ })
    if ([string]::IsNullOrWhiteSpace($url) -or $numeros.Count -eq 0) {
        Write-Log "SMS non envoyé (SMS_HTTP_URL ou ALERTE_SMS_NUMEROS absent du .env) : $Message"
        return $false
    }
    $identifiants = [Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes(
        "$(Get-DotEnvValue 'SMS_HTTP_USER'):$(Get-DotEnvValue 'SMS_HTTP_PASSWORD')"))
    $corps = @{ message = $Message; phoneNumbers = $numeros } | ConvertTo-Json -Compress
    try {
        Invoke-WebRequest -Uri $url -Method Post -UseBasicParsing -TimeoutSec 20 `
            -ContentType 'application/json; charset=utf-8' `
            -Headers @{ Authorization = "Basic $identifiants" } `
            -Body ([Text.Encoding]::UTF8.GetBytes($corps)) | Out-Null
        Write-Log "SMS envoyé à $($numeros -join ', ') : $Message"
        return $true
    } catch {
        Write-Log "Échec d'envoi du SMS : $($_.Exception.Message)"
        return $false
    }
}

function Get-LanIPv4Addresses {
    # Adresses IPv4 des cartes physiques actives (mêmes critères que start-local.ps1).
    if (-not (Get-Command Get-NetAdapter -ErrorAction SilentlyContinue)) { return @() }
    try {
        $indexes = @(Get-NetAdapter -Physical -ErrorAction Stop | Where-Object { $_.Status -eq 'Up' } |
            Select-Object -ExpandProperty ifIndex)
        if ($indexes.Count -eq 0) { return @() }
        return @(Get-NetIPAddress -AddressFamily IPv4 -InterfaceIndex $indexes -ErrorAction Stop |
            Where-Object { $_.IPAddress -notlike '127.*' -and $_.IPAddress -notlike '169.254.*' } |
            Select-Object -ExpandProperty IPAddress -Unique)
    } catch {
        return @()
    }
}

$etat = Get-Etat
$nomServeur = $env:COMPUTERNAME

# ── 1. Point de santé ──────────────────────────────────────────────────────
if (Test-Sante) {
    if ($etat.echecs -gt 0) { Write-Log "Application de nouveau disponible après $($etat.echecs) échec(s)." }
    if ($etat.alerte_envoyee) {
        Send-AlerteSms "YELEN SCHOOL ($nomServeur) : application de nouveau disponible." | Out-Null
    }
    $etat.echecs = 0
    $etat.alerte_envoyee = $false
} else {
    $etat.echecs = [int]$etat.echecs + 1
    Write-Log "Point de santé en échec ($($etat.echecs))."
    if ($etat.echecs -ge $EchecsAvantRedemarrage) {
        Write-Log 'Redémarrage des services...'
        try {
            $null = Invoke-NativeQuiet { powershell.exe -NoProfile -ExecutionPolicy Bypass -File $StartScript }
        } catch {
            Write-Log "Redémarrage impossible : $($_.Exception.Message)"
        }
        Start-Sleep -Seconds 90
        if (Test-Sante) {
            Write-Log 'Application rétablie par le redémarrage automatique.'
            if (-not $etat.alerte_envoyee) {
                Send-AlerteSms "YELEN SCHOOL ($nomServeur) : panne detectee, service relance automatiquement. Verifier le serveur." | Out-Null
            }
            $etat.echecs = 0
            $etat.alerte_envoyee = $false
        } elseif (-not $etat.alerte_envoyee) {
            $etat.alerte_envoyee = Send-AlerteSms "YELEN SCHOOL ($nomServeur) : APPLICATION INDISPONIBLE malgre un redemarrage. Intervention requise."
        }
    }
}

# ── 2. Fraîcheur des sauvegardes (un SMS par jour au plus) ─────────────────
$derniere = Get-ChildItem -Path $BackupDirectory -Filter 'yelen_school_*.dump*' -File -ErrorAction SilentlyContinue |
    Sort-Object LastWriteTime -Descending | Select-Object -First 1
$aujourdhui = Get-Date -Format 'yyyy-MM-dd'
if ($null -eq $derniere -or $derniere.LastWriteTime -lt (Get-Date).AddHours(-$HeuresSansSauvegardeMax)) {
    if ($etat.alerte_sauvegarde -ne $aujourdhui) {
        $detail = if ($null -eq $derniere) { 'aucune sauvegarde trouvee' } else { "derniere sauvegarde le $($derniere.LastWriteTime.ToString('dd/MM/yyyy HH:mm'))" }
        Write-Log "Sauvegarde trop ancienne : $detail"
        Send-AlerteSms "YELEN SCHOOL ($nomServeur) : $detail. Verifier la tache de sauvegarde." | Out-Null
        $etat.alerte_sauvegarde = $aujourdhui
    }
}

Save-Etat $etat

# ── 3. Nouvelle adresse IP du serveur (nouveau réseau, nouvelle box) ───────
# start-local.ps1 autorise l'adresse (ALLOWED_HOSTS, CSRF), reclasse le réseau en
# privé et renouvelle le certificat HTTPS : rien à faire à la main.
$autorisees = @((Get-DotEnvValue 'ALLOWED_HOSTS') -split ',' | ForEach-Object { $_.Trim() } | Where-Object { $_ })
$nouvelles = @(Get-LanIPv4Addresses | Where-Object { $autorisees -notcontains $_ })
if ($autorisees.Count -gt 0 -and $nouvelles.Count -gt 0) {
    Write-Log "Nouvelle adresse IP du serveur : $($nouvelles -join ', ') ; mise à jour de la configuration..."
    try {
        if ((Invoke-NativeQuiet { powershell.exe -NoProfile -ExecutionPolicy Bypass -File $StartScript }) -eq 0) {
            Write-Log 'Configuration mise à jour (voir logs\startup.log).'
        } else {
            Write-Log 'Mise à jour de la configuration en échec (voir logs\startup.log).'
        }
    } catch {
        Write-Log "Mise à jour de la configuration impossible : $($_.Exception.Message)"
    }
}
