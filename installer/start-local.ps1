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

    $content = Get-Content $EnvFile -Raw
    if ($null -eq $content) {
        $content = ''
    }

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
                Write-StartupLog 'AVERTISSEMENT : le pare-feu n’a pas été actualisé.'
            }
        } else {
            Write-StartupLog 'AVERTISSEMENT : script de configuration du pare-feu introuvable.'
        }
    } else {
        Write-StartupLog "Port HTTP conservé : $selectedPort ; règle pare-feu inchangée."
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
