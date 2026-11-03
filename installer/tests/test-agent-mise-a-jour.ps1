#requires -Version 5.1
<##
.SYNOPSIS
    Tests de appliquer-mise-a-jour-en-attente.ps1 (mode EN_LIGNE) sur dépôts Git réels.
    Exécution : pwsh -NoProfile -File installer/tests/test-agent-mise-a-jour.ps1
#>
$ErrorActionPreference = 'Stop'
$agentSource = Join-Path $PSScriptRoot '..\appliquer-mise-a-jour-en-attente.ps1'

$global:UpdateCalls = 0
$global:UpdateExitCode = 0
function powershell.exe {
    $global:UpdateCalls += 1
    $global:LASTEXITCODE = $global:UpdateExitCode
}

function Assert($condition, $message) {
    if (-not $condition) { throw "ÉCHEC : $message" }
    Write-Host "  ok  $message"
}

function Invoke-Git {
    param([string]$Repo)
    & git -C $Repo @args 2>&1 | Out-Null
    if ($LASTEXITCODE -ne 0) { throw "git $args" }
}

function New-AgentFixture {
    $work = Join-Path ([System.IO.Path]::GetTempPath()) ('yelen-agent-' + [guid]::NewGuid().ToString('N'))
    $origin = Join-Path $work 'origin'
    $clone = Join-Path $work 'clone'
    New-Item -ItemType Directory -Path $origin -Force | Out-Null
    Invoke-Git $origin init -q -b main
    Invoke-Git $origin config user.email 't@t'
    Invoke-Git $origin config user.name 't'
    Set-Content -Path (Join-Path $origin 'VERSION') -Value '5.47.8'
    Invoke-Git $origin add -A
    Invoke-Git $origin commit -q -m 'v5.47.8'
    & git clone -q $origin $clone 2>&1 | Out-Null
    New-Item -ItemType Directory -Path (Join-Path $clone 'installer') -Force | Out-Null
    New-Item -ItemType Directory -Path (Join-Path $clone 'mises-a-jour') -Force | Out-Null
    Copy-Item $agentSource (Join-Path $clone 'installer\appliquer-mise-a-jour-en-attente.ps1')
    Set-Content -Path (Join-Path $clone '.env') -Value 'YELEN_HTTP_PORT=8001'
    return @{ Work = $work; Origin = $origin; Clone = $clone }
}

function Write-Demande {
    param([string]$Clone, [hashtable]$Data)
    $json = $Data | ConvertTo-Json -Depth 4
    [System.IO.File]::WriteAllText(
        (Join-Path (Join-Path $Clone 'mises-a-jour') 'demande.json'),
        "$json`n",
        (New-Object System.Text.UTF8Encoding($false))
    )
}

function Read-Demande {
    param([string]$Clone)
    $raw = [System.IO.File]::ReadAllText((Join-Path (Join-Path $Clone 'mises-a-jour') 'demande.json'), [System.Text.Encoding]::UTF8)
    return ($raw | ConvertFrom-Json)
}

# 1. Déjà à jour -> AUCUNE_MAJ sans appeler mettre-a-jour.ps1
$fx = New-AgentFixture
$global:UpdateCalls = 0
Write-Demande $fx.Clone @{ id = '1'; mode = 'EN_LIGNE'; statut = 'VERIFICATION'; version_avant = '5.47.8' }
try { & (Join-Path $fx.Clone 'installer\appliquer-mise-a-jour-en-attente.ps1') -UnePasse } catch { }
$d1 = Read-Demande $fx.Clone
Assert ($d1.statut -eq 'AUCUNE_MAJ' -and $global:UpdateCalls -eq 0) 'EN_LIGNE déjà à jour : AUCUNE_MAJ sans reconstruire'

# 2. Nouvelle version sur origin/main -> appelle mettre-a-jour.ps1 et passe à TERMINEE
Set-Content -Path (Join-Path $fx.Origin 'VERSION') -Value '5.47.9'
Invoke-Git $fx.Origin add -A
Invoke-Git $fx.Origin commit -q -m 'v5.47.9'
$global:UpdateCalls = 0
$global:UpdateExitCode = 0
Write-Demande $fx.Clone @{ id = '2'; mode = 'EN_LIGNE'; statut = 'VERIFICATION'; version_avant = '5.47.8' }
& (Join-Path $fx.Clone 'installer\appliquer-mise-a-jour-en-attente.ps1') -UnePasse
$d2 = Read-Demande $fx.Clone
Assert ($d2.statut -eq 'TERMINEE' -and $d2.version_cible -eq '5.47.9' -and $global:UpdateCalls -eq 1) 'EN_LIGNE nouvelle version : TERMINEE vers 5.47.9'

# 3. Échec de git fetch -> ECHEC consigné dans demande.json et logs/mise-a-jour.log
Invoke-Git $fx.Clone remote set-url origin (Join-Path $fx.Work 'depot-inexistant')
Write-Demande $fx.Clone @{ id = '3'; mode = 'EN_LIGNE'; statut = 'VERIFICATION'; version_avant = '5.47.8' }
& (Join-Path $fx.Clone 'installer\appliquer-mise-a-jour-en-attente.ps1') -UnePasse
$code3 = $LASTEXITCODE
$d3 = Read-Demande $fx.Clone
$log3 = Get-Content (Join-Path (Join-Path $fx.Clone 'logs') 'mise-a-jour.log') -Raw
Assert ($code3 -eq 1 -and $d3.statut -eq 'ECHEC' -and $log3 -match '\[AGENT\] ERREUR') 'EN_LIGNE fetch KO : ECHEC + trace dans mise-a-jour.log'

Remove-Item -LiteralPath $fx.Work -Recurse -Force -ErrorAction SilentlyContinue
Write-Host "Tous les tests de l'agent de mise à jour sont passés."
