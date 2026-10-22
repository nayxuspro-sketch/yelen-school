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
$FirewallScript = Join-Path $PSScriptRoot 'configure-firewall.ps1'
$PortSelectorScript = Join-Path $PSScriptRoot 'resolve-http-port.ps1'
$HostIdScript = Join-Path $PSScriptRoot 'yelen-hostid.ps1'
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

function Set-DotEnvValue {
    param(
        [string]$Name,
        [string]$Value
    )

    # Lecture explicite en UTF-8 : sans BOM, Windows PowerShell lirait le fichier
    # en ANSI et altérerait les accents des commentaires à chaque réécriture.
    $content = [System.IO.File]::ReadAllText($EnvFile, [System.Text.UTF8Encoding]::new($false))

    $escapedName = [regex]::Escape($Name)
    $line = "$Name=$Value"
    if ([regex]::IsMatch($content, "(?m)^$escapedName=.*$")) {
        $content = [regex]::Replace(
            $content,
            "(?m)^$escapedName=.*$",
            [System.Text.RegularExpressions.MatchEvaluator]{ param($match) $line }
        )
    } else {
        $separator = if ($content.EndsWith("`n")) { '' } else { "`r`n" }
        $content = "$content$separator$line`r`n"
    }

    [System.IO.File]::WriteAllText(
        $EnvFile,
        $content,
        [System.Text.UTF8Encoding]::new($false)
    )
}

function Add-DotEnvListValues {
    # Complète une liste séparée par des virgules sans rien retirer et retourne
    # les valeurs ajoutées. Une variable absente ou vide est laissée telle
    # quelle : c'est à l'installateur de la créer.
    param(
        [string]$Name,
        [string[]]$Values
    )

    $current = Get-DotEnvValue $Name
    if ([string]::IsNullOrWhiteSpace($current)) { return @() }
    $items = @($current -split ',' | ForEach-Object { $_.Trim() } | Where-Object { $_ })
    $added = @($Values | Select-Object -Unique | Where-Object { $items -notcontains $_ })
    if ($added.Count -gt 0) {
        Set-DotEnvValue $Name (($items + $added) -join ',')
    }
    return $added
}

function Get-PhysicalInterfaceIndexes {
    # Cartes réseau physiques actives (Wi-Fi, Ethernet). Les cartes virtuelles
    # (WSL, Hyper-V, Docker) changent d'adresse à chaque démarrage et ne sont
    # jamais jointes depuis les autres postes.
    if (-not (Get-Command Get-NetAdapter -ErrorAction SilentlyContinue)) { return @() }
    try {
        return @(Get-NetAdapter -Physical -ErrorAction Stop |
            Where-Object { $_.Status -eq 'Up' } |
            Select-Object -ExpandProperty ifIndex)
    } catch {
        return @()
    }
}

function Get-LanIPv4Addresses {
    param([uint32[]]$InterfaceIndexes)

    if ($InterfaceIndexes.Count -eq 0) { return @() }
    try {
        return @(Get-NetIPAddress -AddressFamily IPv4 -InterfaceIndex $InterfaceIndexes -ErrorAction Stop |
            Where-Object { $_.IPAddress -notlike '127.*' -and $_.IPAddress -notlike '169.254.*' } |
            Select-Object -ExpandProperty IPAddress -Unique)
    } catch {
        return @()
    }
}

function Get-PublicNetworkNames {
    # Réseaux classés « Public » sur les cartes physiques : la règle de pare-feu
    # YELEN ne s'y applique pas, les autres postes ne peuvent pas se connecter.
    param([uint32[]]$InterfaceIndexes)

    if ($InterfaceIndexes.Count -eq 0 -or -not (Get-Command Get-NetConnectionProfile -ErrorAction SilentlyContinue)) {
        return @()
    }
    try {
        return @(Get-NetConnectionProfile -ErrorAction Stop |
            Where-Object { $_.NetworkCategory -eq 'Public' -and $InterfaceIndexes -contains $_.InterfaceIndex } |
            ForEach-Object { "$($_.Name) ($($_.InterfaceAlias))" })
    } catch {
        return @()
    }
}

function Register-LanAddresses {
    # Autorise les adresses IP actuelles du poste (ALLOWED_HOSTS et
    # CSRF_TRUSTED_ORIGINS) : l'application suit le poste d'un réseau à l'autre.
    # Retourne les adresses nouvellement autorisées.
    param(
        [string[]]$Addresses,
        [int]$HttpPort
    )

    if ($Addresses.Count -eq 0) { return @() }
    $origins = @($Addresses | ForEach-Object { "http://${_}:$HttpPort" })
    if ((Get-DotEnvValue 'YELEN_HTTPS') -eq 'true') {
        $httpsPort = Get-DotEnvValue 'YELEN_HTTPS_PORT'
        if ([string]::IsNullOrWhiteSpace($httpsPort)) { $httpsPort = '8443' }
        $origins += @($Addresses | ForEach-Object { "https://${_}:$httpsPort" })
    }
    $added = @(Add-DotEnvListValues 'ALLOWED_HOSTS' $Addresses)
    Add-DotEnvListValues 'CSRF_TRUSTED_ORIGINS' $origins | Out-Null
    return $added
}

function Test-FirewallRuleForPort {
    param([int]$Port)

    if (-not (Get-Command Get-NetFirewallRule -ErrorAction SilentlyContinue)) {
        return $false
    }

    try {
        $rules = @(Get-NetFirewallRule -Name 'YELEN_SCHOOL_LocalWeb' -ErrorAction SilentlyContinue)
        foreach ($rule in $rules) {
            $profile = $rule.Profile.ToString()
            if (
                $rule.Enabled -ne 'True' -or
                $rule.Direction -ne 'Inbound' -or
                $rule.Action -ne 'Allow' -or
                $profile -notmatch 'Domain' -or
                $profile -notmatch 'Private' -or
                $profile -match 'Public' -or
                $rule.EdgeTraversalPolicy -ne 'Block'
            ) {
                continue
            }

            $portFilters = @($rule | Get-NetFirewallPortFilter -ErrorAction Stop)
            $addressFilters = @($rule | Get-NetFirewallAddressFilter -ErrorAction Stop)
            $portOk = $portFilters | Where-Object {
                $_.Protocol -eq 'TCP' -and $_.LocalPort.ToString() -eq [string]$Port
            }
            $addressOk = $addressFilters | Where-Object {
                @($_.RemoteAddress) -contains 'LocalSubnet'
            }
            if ($portOk -and $addressOk) {
                return $true
            }
        }
        return $false
    } catch {
        return $false
    }
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

    if (-not (Test-Path $PortSelectorScript)) {
        throw "Script de sélection de port introuvable : $PortSelectorScript"
    }
    . $PortSelectorScript

    $requestedPortText = Get-DotEnvValue 'YELEN_HTTP_PORT'
    if ([string]::IsNullOrWhiteSpace($requestedPortText)) {
        $requestedPortText = '8000'
    }
    $requestedPort = 0
    if (-not [int]::TryParse($requestedPortText, [ref]$requestedPort) -or $requestedPort -lt 1 -or $requestedPort -gt 65535) {
        throw 'YELEN_HTTP_PORT doit être un port compris entre 1 et 65535.'
    }

    try {
        $selectedPort = Select-YelenHttpPort -Root $Root -ComposeFile $ComposeFile -PreferredPort $requestedPort
    } catch {
        throw $_.Exception.Message
    }

    $configuredPortLine = Get-Content $EnvFile |
        Where-Object { $_ -match '^YELEN_HTTP_PORT=' } |
        Select-Object -First 1
    $portValueMissing = $null -eq $configuredPortLine
    $portChanged = $selectedPort -ne $requestedPort
    if ($portChanged -or $portValueMissing) {
        Set-DotEnvValue 'YELEN_HTTP_PORT' ([string]$selectedPort)
    }

    $firewallNeedsUpdate = $portChanged -or
        (-not (Test-FirewallRuleForPort -Port $selectedPort))

    if ($firewallNeedsUpdate) {
        if ($portChanged) {
            Write-StartupLog "Le port TCP $requestedPort est occupé. Port sélectionné automatiquement : $selectedPort."
        } else {
            Write-StartupLog "La règle du pare-feu ne correspond pas au port TCP $selectedPort. Synchronisation nécessaire."
        }

        # La tâche planifiée est enregistrée avec le niveau d'exécution élevé.
        # Lors d'un démarrage normal la règle conforme est donc conservée sans
        # nouvelle UAC ; une demande ne survient qu'après un changement ou une
        # absence de règle.
        if (Test-Path $FirewallScript) {
            & powershell.exe -NoProfile -ExecutionPolicy Bypass -File $FirewallScript -Port $selectedPort
            if ($LASTEXITCODE -ne 0) {
                Write-StartupLog 'AVERTISSEMENT : le pare-feu n''a pas été actualisé.'
            }
        } else {
            Write-StartupLog 'AVERTISSEMENT : script de configuration du pare-feu introuvable.'
        }
    } else {
        Write-StartupLog "Port HTTP conservé : $selectedPort ; règle pare-feu inchangée."
    }

    # Adresses IP actuelles du poste : autorisées automatiquement pour que
    # l'application reste joignable après un changement de réseau (box, Wi-Fi).
    # Si .env change, docker compose recrée le service web.
    $physicalIndexes = @(Get-PhysicalInterfaceIndexes)
    $lanAddresses = @(Get-LanIPv4Addresses -InterfaceIndexes $physicalIndexes)
    $newAddresses = @(Register-LanAddresses -Addresses $lanAddresses -HttpPort $selectedPort)
    if ($newAddresses.Count -gt 0) {
        Write-StartupLog "Nouvelle(s) adresse(s) du poste autorisée(s) : $($newAddresses -join ', ')."
    }
    $publicNetworks = @(Get-PublicNetworkNames -InterfaceIndexes $physicalIndexes)
    if ($publicNetworks.Count -gt 0) {
        Write-StartupLog "AVERTISSEMENT : réseau classé Public ($($publicNetworks -join ', ')) : le pare-feu Windows bloque l'accès des autres postes. Classer ce réseau en « Réseau privé » (Paramètres > Réseau et Internet)."
    }

    # Empreinte du serveur transmise au conteneur (liaison de la licence).
    if (-not (Test-Path $HostIdScript)) {
        throw "Script d'empreinte serveur introuvable : $HostIdScript"
    }
    . $HostIdScript
    $env:YELEN_HOST_ID = Get-YelenHostId

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
        $url = "http://127.0.0.1:$port/accounts/login/"
        if ((Get-DotEnvValue 'YELEN_HTTPS') -eq 'true') {
            $httpsPort = Get-DotEnvValue 'YELEN_HTTPS_PORT'
            if ([string]::IsNullOrWhiteSpace($httpsPort)) { $httpsPort = '8443' }
            $url = "https://127.0.0.1:$httpsPort/accounts/login/"
        }
        Start-Process $url
    }
} catch {
    Write-StartupLog "ERREUR : $($_.Exception.Message)"
    exit 1
}
