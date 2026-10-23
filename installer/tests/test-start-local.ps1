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
function Get-ServerHostName { 'desktop-nkqmf8l' }   # casse différente du .env : pas de doublon attendu
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
    $newHosts = @(Register-ServerHosts -Hosts ($lanAddresses + @(Get-ServerNames)) -HttpPort $selectedPort)
    if ($newHosts.Count -gt 0) {
        Write-StartupLog "Nouvelle(s) adresse(s) du poste autorisée(s) : $($newHosts -join ', ')."
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
    Write-Host '1. Nouveau réseau : la nouvelle adresse et les noms du serveur sont autorisés'
    $lan = Invoke-StartupBlock
    Assert ($lan.Count -eq 1 -and $lan[0] -eq '10.52.237.38') "seule l'adresse de la carte physique active est retenue (ni APIPA, ni WSL, ni carte déconnectée)"
    Assert ((Get-EnvLine 'ALLOWED_HOSTS') -eq 'ALLOWED_HOSTS=localhost,127.0.0.1,DESKTOP-NKQMF8L,192.168.1.10,10.52.237.38,desktop-nkqmf8l.local') 'ALLOWED_HOSTS : adresse et NOMPC.local ajoutés, NOMPC déjà présent (casse ignorée), anciennes valeurs conservées'
    Assert ((Get-EnvLine 'CSRF_TRUSTED_ORIGINS') -eq 'CSRF_TRUSTED_ORIGINS=http://localhost:8001,http://192.168.1.10:8001,http://10.52.237.38:8001,http://desktop-nkqmf8l:8001,http://desktop-nkqmf8l.local:8001') 'CSRF_TRUSTED_ORIGINS : origines http de l''adresse et des deux noms'
    $bytes = [System.IO.File]::ReadAllBytes($EnvFile)
    Assert (-not ($bytes[0] -eq 0xEF -and $bytes[1] -eq 0xBB)) '.env écrit sans BOM'
    $text = [System.IO.File]::ReadAllText($EnvFile, [System.Text.UTF8Encoding]::new($false))
    Assert ($text.Contains('# Contrôle des licences (anti-fraude) : accès réservé')) 'accents des commentaires intacts'
    Assert ($text.StartsWith("SECRET_KEY=x`r`n")) 'autres lignes inchangées'
    $log = [System.IO.File]::ReadAllText($LogFile)
    Assert ($log -match 'Nouvelle\(s\) adresse\(s\) du poste autorisée\(s\) : 10\.52\.237\.38, desktop-nkqmf8l\.local\.') 'journal : adresse et nom ajoutés'
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
    Assert ($lan[0] -eq '192.168.1.10' -and (Get-EnvLine 'ALLOWED_HOSTS') -like '*192.168.1.10,10.52.237.38,desktop-nkqmf8l.local') 'liste inchangée'

    Write-Host '4. HTTPS actif : les origines https sont ajoutées'
    $script:Adapters[0].Status = 'Up'; $script:Ips[0].IPAddress = '10.0.0.5'
    [System.IO.File]::AppendAllText($EnvFile, "YELEN_HTTPS=true`r`nYELEN_HTTPS_PORT=8443`r`n", [System.Text.UTF8Encoding]::new($false))
    $null = Invoke-StartupBlock
    $csrf = Get-EnvLine 'CSRF_TRUSTED_ORIGINS'
    Assert ($csrf.EndsWith(',http://10.0.0.5:8001,https://10.0.0.5:8443,https://192.168.1.10:8443,https://desktop-nkqmf8l:8443,https://desktop-nkqmf8l.local:8443')) 'origines http et https pour les deux cartes actives et les noms'

    Write-Host "5. Variable absente du .env : rien n'est créé"
    [System.IO.File]::WriteAllText($EnvFile, "SECRET_KEY=x`r`n", [System.Text.UTF8Encoding]::new($false))
    $null = Invoke-StartupBlock
    Assert ([System.IO.File]::ReadAllText($EnvFile) -eq "SECRET_KEY=x`r`n") '.env intact'

    Write-Host '6. Aucune carte physique active : pas d''adresse, les noms du serveur restent autorisés'
    $script:Adapters | ForEach-Object { $_.Status = 'Disconnected' }
    [System.IO.File]::WriteAllText($EnvFile, $envText, [System.Text.UTF8Encoding]::new($false))
    $lan = Invoke-StartupBlock
    Assert ($lan.Count -eq 0) 'aucune adresse retenue'
    Assert ((Get-EnvLine 'ALLOWED_HOSTS') -eq 'ALLOWED_HOSTS=localhost,127.0.0.1,DESKTOP-NKQMF8L,192.168.1.10,desktop-nkqmf8l.local') 'seul NOMPC.local est ajouté'

    Write-Host '7. Serveur sans nom : aucune entrée de nom'
    function Get-ServerHostName { '' }
    [System.IO.File]::WriteAllText($EnvFile, $envText, [System.Text.UTF8Encoding]::new($false))
    $null = Invoke-StartupBlock
    Assert ([System.IO.File]::ReadAllText($EnvFile) -eq $envText) '.env intact'

    Write-Host '8. Set-DotEnvValue relit le fichier en UTF-8'
    Set-DotEnvValue 'YELEN_HTTP_PORT' '8002'
    $text = [System.IO.File]::ReadAllText($EnvFile, [System.Text.UTF8Encoding]::new($false))
    Assert ($text.Contains('Contrôle des licences') -and $text.Contains('YELEN_HTTP_PORT=8002')) 'accents intacts après réécriture'

    Write-Host '9. HTTPS inactif : aucun renouvellement de certificat'
    [System.IO.File]::WriteAllText($EnvFile, $envText, [System.Text.UTF8Encoding]::new($false))
    $script:DockerCalls = @()
    $script:DockerExitCode = 0
    $script:CertNotAfter = (Get-Date).ToUniversalTime().AddDays(400)
    function docker {
        $script:DockerCalls += ,@($args)
        if ($script:DockerExitCode -eq 0) { $script:CertNotAfter = (Get-Date).ToUniversalTime().AddDays(825) }
        $global:LASTEXITCODE = $script:DockerExitCode
    }
    function Get-CertificateNotAfter { param([string]$Path) $script:CertNotAfter }
    $hosts = @('10.52.237.38', 'desktop-nkqmf8l', 'desktop-nkqmf8l.local')
    Assert (-not (Update-ServerCertificate -Hosts $hosts) -and $script:DockerCalls.Count -eq 0) 'sans YELEN_HTTPS=true : rien à faire, docker non appelé'

    Write-Host '10. HTTPS actif, certificat valide couvrant les adresses actuelles : rien à faire'
    [System.IO.File]::AppendAllText($EnvFile, "YELEN_HTTPS=true`r`nYELEN_HTTPS_HOSTS=10.52.237.38,DESKTOP-NKQMF8L,DESKTOP-NKQMF8L.local,localhost,127.0.0.1`r`n", [System.Text.UTF8Encoding]::new($false))
    Assert (-not (Update-ServerCertificate -Hosts $hosts) -and $script:DockerCalls.Count -eq 0) 'adresses couvertes (casse ignorée) et certificat valide : docker non appelé'

    Write-Host '11. Nouvelle adresse IP : certificat renouvelé, liste complétée'
    Remove-Item $LogFile -ErrorAction SilentlyContinue
    $renewed = Update-ServerCertificate -Hosts (@('192.168.11.108') + $hosts)
    Assert ($renewed -eq $true -and $script:DockerCalls.Count -eq 1) 'un appel docker, renouvellement signalé'
    $call = $script:DockerCalls[0]
    Assert (($call -join ' ') -like 'compose -f * run --rm --no-deps --entrypoint python web /app/installer/generer-certificats.py --hosts 10.52.237.38,DESKTOP-NKQMF8L,DESKTOP-NKQMF8L.local,localhost,127.0.0.1,192.168.11.108 --out /app/certs') 'generer-certificats.py reçoit les anciennes adresses puis la nouvelle (autorité réutilisée)'
    Assert ((Get-EnvLine 'YELEN_HTTPS_HOSTS') -eq 'YELEN_HTTPS_HOSTS=10.52.237.38,DESKTOP-NKQMF8L,DESKTOP-NKQMF8L.local,localhost,127.0.0.1,192.168.11.108') 'YELEN_HTTPS_HOSTS complété'
    $log = [System.IO.File]::ReadAllText($LogFile)
    Assert ($log -match 'Renouvellement du certificat HTTPS \(nouvelle\(s\) adresse\(s\) : 192\.168\.11\.108\)' -and $log -match 'Certificat HTTPS renouvelé') 'journal : motif et confirmation'
    Assert (-not (Update-ServerCertificate -Hosts (@('192.168.11.108') + $hosts)) -and $script:DockerCalls.Count -eq 1) 'second passage : plus rien à faire'

    Write-Host '12. Certificat expirant dans moins de 30 jours : renouvelé'
    $script:CertNotAfter = (Get-Date).ToUniversalTime().AddDays(10)
    Assert ((Update-ServerCertificate -Hosts $hosts) -eq $true -and $script:DockerCalls.Count -eq 2) 'renouvellement anticipé'
    Assert ([System.IO.File]::ReadAllText($LogFile) -match 'certificat serveur expirant le') 'journal : motif expiration'

    Write-Host '13. Échec de la génération : avertissement, .env inchangé, pas de redémarrage du proxy'
    $script:DockerExitCode = 1
    $script:CertNotAfter = $null
    $before = Get-EnvLine 'YELEN_HTTPS_HOSTS'
    Assert (-not (Update-ServerCertificate -Hosts (@('10.0.0.9') + $hosts)) -and $script:DockerCalls.Count -eq 3) 'retourne $false après l''appel docker'
    Assert ((Get-EnvLine 'YELEN_HTTPS_HOSTS') -eq $before) 'YELEN_HTTPS_HOSTS inchangé'
    Assert ([System.IO.File]::ReadAllText($LogFile) -match 'relancer activer-https.bat') 'journal : consigne de reprise manuelle'

    Write-Host '14. Progression de docker compose sur la sortie d''erreur : renouvellement mené à bien sous $ErrorActionPreference = Stop'
    $script:DockerExitCode = 0
    $script:CertNotAfter = (Get-Date).ToUniversalTime().AddDays(400)
    function docker {
        $script:DockerCalls += ,@($args)
        Write-Error ' Container yelen-school-web-run-cc2783af306b Creating'   # ce que Windows PowerShell fait du flux d'erreur natif
        $script:CertNotAfter = (Get-Date).ToUniversalTime().AddDays(825)
        $global:LASTEXITCODE = 0
    }
    $renewed = $false
    try { $renewed = Update-ServerCertificate -Hosts (@('10.52.237.43') + $hosts) } catch { Assert $false "exception : $($_.Exception.Message)" }
    Assert ($renewed -eq $true -and $script:DockerCalls.Count -eq 4) 'la sortie d''erreur de docker n''interrompt pas le script ; certificat renouvelé'
    Assert ((Invoke-NativeQuiet { docker info }) -eq 0) 'Invoke-NativeQuiet retourne le code de retour malgré la sortie d''erreur'

    Write-Host 'Tous les tests passent.' -ForegroundColor Green
} finally {
    Remove-Item -Recurse -Force $work -ErrorAction SilentlyContinue
}
