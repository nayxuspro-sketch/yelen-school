#requires -Version 5.1
<##
.SYNOPSIS
    Tests de surveiller-yelen.ps1 : détection d'une nouvelle adresse IP du serveur.
    Exécution : pwsh -NoProfile -File installer/tests/test-surveiller-yelen.ps1
    (Windows PowerShell 5.1 ou PowerShell 7 ; aucun service Docker requis.)
#>
$ErrorActionPreference = 'Stop'

# Bloc « 3. Nouvelle adresse IP » du script, exécuté avec des doublures.
$scriptPath = Join-Path $PSScriptRoot '..\surveiller-yelen.ps1'
$script = [System.IO.File]::ReadAllText($scriptPath, [System.Text.UTF8Encoding]::new($true))
$block = $script.Substring($script.IndexOf('# ── 3. Nouvelle adresse IP'))
$work = Join-Path ([System.IO.Path]::GetTempPath()) ("yelen-surveiller-" + [guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Path $work -Force | Out-Null
$blockFile = Join-Path $work 'bloc.ps1'
[System.IO.File]::WriteAllText($blockFile, $block, [System.Text.UTF8Encoding]::new($true))

$script:Env = @{ ALLOWED_HOSTS = 'localhost,127.0.0.1,DESKTOP-NKQMF8L,10.52.237.38' }
$script:Lan = @('10.52.237.38')
$script:Journal = @()
$script:Relances = 0
$StartScript = 'C:\YELEN-SCHOOL\installer\start-local.ps1'
function Get-DotEnvValue { param([string]$Name) if ($script:Env.ContainsKey($Name)) { $script:Env[$Name] } else { '' } }
function Get-LanIPv4Addresses { $script:Lan }
function Write-Log { param([string]$Message) $script:Journal += $Message }
function powershell.exe { $script:Relances++; $global:LASTEXITCODE = 0 }

function Assert($condition, $message) {
    if (-not $condition) { throw "ÉCHEC : $message" }
    Write-Host "  ok  $message"
}

try {
    Write-Host '1. Adresse déjà autorisée : rien à faire'
    . $blockFile
    Assert ($script:Relances -eq 0 -and $script:Journal.Count -eq 0) 'start-local.ps1 non relancé, journal vide'

    Write-Host '2. Nouvelle adresse (nouveau réseau) : start-local.ps1 relancé'
    $script:Lan = @('192.168.11.108')
    . $blockFile
    Assert ($script:Relances -eq 1) 'start-local.ps1 relancé une fois'
    Assert ($script:Journal[0] -eq 'Nouvelle adresse IP du serveur : 192.168.11.108 ; mise à jour de la configuration...') 'journal : adresse détectée'
    Assert ($script:Journal[1] -like 'Configuration mise à jour*') 'journal : confirmation'

    Write-Host '3. ALLOWED_HOSTS absent du .env : aucune relance (configuration gérée par l''installateur)'
    $script:Env = @{}
    $script:Relances = 0
    . $blockFile
    Assert ($script:Relances -eq 0) 'aucune relance'

    Write-Host '4. Aucune carte physique active : aucune relance'
    $script:Env = @{ ALLOWED_HOSTS = 'localhost' }
    $script:Lan = @()
    . $blockFile
    Assert ($script:Relances -eq 0) 'aucune relance'

    Write-Host 'Tous les tests passent.' -ForegroundColor Green
} finally {
    Remove-Item -Recurse -Force $work -ErrorAction SilentlyContinue
}
