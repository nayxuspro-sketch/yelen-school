#requires -Version 5.1
<##
.SYNOPSIS
    Tests de start-local.ps1 : autorisation automatique des adresses IP du poste.
    Exécution : pwsh -NoProfile -File installer/tests/test-start-local.ps1
    (Windows PowerShell 5.1 ou PowerShell 7 ; aucun service Docker requis.)
#>
$ErrorActionPreference = 'Stop'

# Fonctions du script (tout ce qui précède le corps principal), sans son en-tête.
$scriptPath = Join-Path $PSScriptRoot '..\start-local.ps1'
$script = [System.IO.File]::ReadAllText($scriptPath, [System.Text.UTF8Encoding]::new($false))
$defs = $script.Substring(0, $script.IndexOf('New-Item -ItemType Directory -Path $LogDirectory'))
$defs = $defs -replace '(?m)^#requires.*$', '' -replace '(?s)\[CmdletBinding\(\)\]\s*param\(\s*\[switch\]\$OpenBrowser\s*\)', ''
$work = Join-Path ([System.IO.Path]::GetTempPath()) ("yelen-start-local-" + [guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Path $work -Force | Out-Null
$defsFile = Join-Path $work 'defs.ps1'
[System.IO.File]::WriteAllText($defsFile, $defs, [System.Text.UTF8Encoding]::new($true))
. $defsFile
$EnvFile = Join-Path $work '.env'
$LogFile = Join-Path $work 'startup.log'

# ── Doublures des cmdlets Windows ─────────────────────────────────────────────
$script:Adapters = @(
    [pscustomobject]@{ Name = 'Wi-Fi'; Status = 'Up'; ifIndex = [uint32]12 },
    [pscustomobject]@{ Name = 'Ethernet'; Status = 'Disconnected'; ifIndex = [uint32]7 }
)
$script:Ips = @(
    [pscustomobject]@{ IPAddress = '10.52.237.38'; InterfaceIndex = [uint32]12 },
    [pscustomobject]@{ IPAddress = '169.254.3.9'; InterfaceIndex = [uint32]12 },
    [pscustomobject]@{ IPAddress = '172.26.208.1'; InterfaceIndex = [uint32]40 },   # vEthernet (WSL)
    [pscustomobject]@{ IPAddress = '192.168.1.10'; InterfaceIndex = [uint32]7 }
)
$script:Profiles = @(
    [pscustomobject]@{ Name = 'Maison 4G'; InterfaceAlias = 'Wi-Fi'; InterfaceIndex = [uint32]12; NetworkCategory = 'Public' },
    [pscustomobject]@{ Name = 'Réseau non identifié'; InterfaceAlias = 'vEthernet (WSL)'; InterfaceIndex = [uint32]40; NetworkCategory = 'Public' }
)
function Get-NetAdapter { param([switch]$Physical, $ErrorAction) $script:Adapters }
function Get-NetIPAddress {
    param($AddressFamily, [uint32[]]$InterfaceIndex, $ErrorAction)
    $script:Ips | Where-Object { $InterfaceIndex -contains $_.InterfaceIndex }
}
function Get-NetConnectionProfile { param($ErrorAction) $script:Profiles }
function Write-StartupLog { param([string]$Message) Add-Content -Path $LogFile -Value $Message }

function Assert($condition, $message) {
    if (-not $condition) { throw "ÉCHEC : $message" }
    Write-Host "  ok  $message"
}
function Get-EnvLine($name) { [System.IO.File]::ReadAllLines($EnvFile) | Where-Object { $_ -like "$name=*" } }

# Même enchaînement que le corps principal de start-local.ps1.
function Invoke-StartupBlock {
    $selectedPort = 8001
    $physicalIndexes = @(Get-PhysicalInterfaceIndexes)
    $lanAddresses = @(Get-LanIPv4Addresses -InterfaceIndexes $physicalIndexes)
    $newAddresses = @(Register-LanAddresses -Addresses $lanAddresses -HttpPort $selectedPort)
    if ($newAddresses.Count -gt 0) {
        Write-StartupLog "Nouvelle(s) adresse(s) du poste autorisée(s) : $($newAddresses -join ', ')."
    }
    $publicNetworks = @(Get-PublicNetworkNames -InterfaceIndexes $physicalIndexes)
    if ($publicNetworks.Count -gt 0) {
        Write-StartupLog "AVERTISSEMENT : réseau classé Public ($($publicNetworks -join ', '))"
    }
    return ,$lanAddresses
}

$envText = "SECRET_KEY=x`r`n# Contrôle des licences (anti-fraude) : accès réservé`r`nYELEN_HTTP_PORT=8001`r`n" +
    "ALLOWED_HOSTS=localhost,127.0.0.1,DESKTOP-NKQMF8L,192.168.1.10`r`n" +
    "CSRF_TRUSTED_ORIGINS=http://localhost:8001,http://192.168.1.10:8001`r`n"
[System.IO.File]::WriteAllText($EnvFile, $envText, [System.Text.UTF8Encoding]::new($false))

try {
    Write-Host '1. Nouveau réseau : la nouvelle adresse est autorisée'
    $lan = Invoke-StartupBlock
    Assert ($lan.Count -eq 1 -and $lan[0] -eq '10.52.237.38') "seule l'adresse de la carte physique active est retenue (ni APIPA, ni WSL, ni carte déconnectée)"
    Assert ((Get-EnvLine 'ALLOWED_HOSTS') -eq 'ALLOWED_HOSTS=localhost,127.0.0.1,DESKTOP-NKQMF8L,192.168.1.10,10.52.237.38') 'ALLOWED_HOSTS complété, anciennes valeurs conservées'
    Assert ((Get-EnvLine 'CSRF_TRUSTED_ORIGINS') -eq 'CSRF_TRUSTED_ORIGINS=http://localhost:8001,http://192.168.1.10:8001,http://10.52.237.38:8001') 'CSRF_TRUSTED_ORIGINS complété avec le port HTTP'
    $bytes = [System.IO.File]::ReadAllBytes($EnvFile)
    Assert (-not ($bytes[0] -eq 0xEF -and $bytes[1] -eq 0xBB)) '.env écrit sans BOM'
    $text = [System.IO.File]::ReadAllText($EnvFile, [System.Text.UTF8Encoding]::new($false))
    Assert ($text.Contains('# Contrôle des licences (anti-fraude) : accès réservé')) 'accents des commentaires intacts'
    Assert ($text.StartsWith("SECRET_KEY=x`r`n")) 'autres lignes inchangées'
    $log = [System.IO.File]::ReadAllText($LogFile)
    Assert ($log -match 'Nouvelle\(s\) adresse\(s\) du poste autorisée\(s\) : 10\.52\.237\.38\.') 'journal : adresse ajoutée'
    Assert ($log -match 'AVERTISSEMENT : réseau classé Public \(Maison 4G \(Wi-Fi\)\)') 'journal : réseau Public signalé pour la carte physique'
    Assert (-not ($log -match 'vEthernet')) 'aucun avertissement pour la carte virtuelle WSL'

    Write-Host '2. Second démarrage : idempotent'
    $before = [System.IO.File]::ReadAllBytes($EnvFile)
    Remove-Item $LogFile
    $null = Invoke-StartupBlock
    Assert ([System.Linq.Enumerable]::SequenceEqual($before, [System.IO.File]::ReadAllBytes($EnvFile))) '.env identique octet pour octet'
    Assert (-not (Test-Path $LogFile) -or -not ([System.IO.File]::ReadAllText($LogFile) -match 'Nouvelle')) 'aucune ligne « Nouvelle adresse »'

    Write-Host "3. Retour sur l'ancien réseau : rien à ajouter"
    $script:Adapters[0].Status = 'Disconnected'; $script:Adapters[1].Status = 'Up'
    $lan = Invoke-StartupBlock
    Assert ($lan[0] -eq '192.168.1.10' -and (Get-EnvLine 'ALLOWED_HOSTS') -like '*192.168.1.10,10.52.237.38') 'liste inchangée'

    Write-Host '4. HTTPS actif : les origines https sont ajoutées'
    $script:Adapters[0].Status = 'Up'; $script:Ips[0].IPAddress = '10.0.0.5'
    [System.IO.File]::AppendAllText($EnvFile, "YELEN_HTTPS=true`r`nYELEN_HTTPS_PORT=8443`r`n", [System.Text.UTF8Encoding]::new($false))
    $null = Invoke-StartupBlock
    $csrf = Get-EnvLine 'CSRF_TRUSTED_ORIGINS'
    Assert ($csrf.EndsWith(',http://10.0.0.5:8001,https://10.0.0.5:8443,https://192.168.1.10:8443')) 'origines http et https pour les deux cartes actives'

    Write-Host "5. Variable absente du .env : rien n'est créé"
    [System.IO.File]::WriteAllText($EnvFile, "SECRET_KEY=x`r`n", [System.Text.UTF8Encoding]::new($false))
    $null = Invoke-StartupBlock
    Assert ([System.IO.File]::ReadAllText($EnvFile) -eq "SECRET_KEY=x`r`n") '.env intact'

    Write-Host '6. Aucune carte physique active : rien à faire'
    $script:Adapters | ForEach-Object { $_.Status = 'Disconnected' }
    [System.IO.File]::WriteAllText($EnvFile, $envText, [System.Text.UTF8Encoding]::new($false))
    $lan = Invoke-StartupBlock
    Assert ($lan.Count -eq 0 -and [System.IO.File]::ReadAllText($EnvFile) -eq $envText) 'aucune adresse, .env intact'

    Write-Host '7. Set-DotEnvValue relit le fichier en UTF-8'
    Set-DotEnvValue 'YELEN_HTTP_PORT' '8002'
    $text = [System.IO.File]::ReadAllText($EnvFile, [System.Text.UTF8Encoding]::new($false))
    Assert ($text.Contains('Contrôle des licences') -and $text.Contains('YELEN_HTTP_PORT=8002')) 'accents intacts après réécriture'

    Write-Host 'Tous les tests passent.' -ForegroundColor Green
} finally {
    Remove-Item -Recurse -Force $work -ErrorAction SilentlyContinue
}
