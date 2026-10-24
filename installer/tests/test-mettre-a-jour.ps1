#requires -Version 5.1
<##
.SYNOPSIS
    Tests de mettre-a-jour.ps1 : dépôt git réel (origine locale), docker / start-local /
    sauvegarde / santé doublés. Exécution : pwsh -NoProfile -File installer/tests/test-mettre-a-jour.ps1
#>
$ErrorActionPreference = 'Stop'
$scriptSource = Join-Path $PSScriptRoot '..\mettre-a-jour.ps1'

# ── Doublures ────────────────────────────────────────────────────────────────
$global:Calls = [System.Collections.Generic.List[string]]::new()
$global:BuildExitCode = 0
$global:StartExitCode = 0
$global:BackupExitCode = 0
$global:HealthVersion = ''
function docker {
    $global:Calls.Add("docker $($args -join ' ')")
    if ($args -contains 'build') { $global:LASTEXITCODE = $global:BuildExitCode } else { $global:LASTEXITCODE = 0 }
}
function powershell.exe {
    $file = [System.IO.Path]::GetFileName($args[$args.IndexOf('-File') + 1])
    $global:Calls.Add($file)
    if ($file -eq 'backup-windows.ps1') { $global:LASTEXITCODE = $global:BackupExitCode } else { $global:LASTEXITCODE = $global:StartExitCode }
}
function Invoke-WebRequest {
    param($Uri, [switch]$UseBasicParsing, $TimeoutSec)
    if (-not $global:HealthVersion) { throw 'connexion refusée' }
    [pscustomobject]@{ Content = ('{"status": "ok", "version": "' + $global:HealthVersion + '"}') }
}
function Start-Sleep { param($Seconds) }

function Assert($condition, $message) {
    if (-not $condition) { throw "ÉCHEC : $message" }
    Write-Host "  ok  $message"
}

# ── Dépôts : origine locale (v5.1.0 puis v5.2.0) et clone installé en v5.1.0 ────
function Invoke-Git { param([string]$Repo) & git -C $Repo @args 2>&1 | Out-Null; if ($LASTEXITCODE -ne 0) { throw "git $args" } }
function New-Fixture {
    $work = Join-Path ([System.IO.Path]::GetTempPath()) ('yelen-maj-' + [guid]::NewGuid().ToString('N'))
    $origin = Join-Path $work 'origin'; $clone = Join-Path $work 'clone'
    New-Item -ItemType Directory -Path $origin -Force | Out-Null
    Invoke-Git $origin init -q -b main
    Invoke-Git $origin config user.email 't@t'; Invoke-Git $origin config user.name 't'
    Set-Content -Path (Join-Path $origin 'VERSION') -Value '5.1.0'
    New-Item -ItemType Directory -Path (Join-Path $origin 'docs') -Force | Out-Null
    Set-Content -Path (Join-Path $origin 'docs\guide.md') -Value 'v1'
    Invoke-Git $origin add -A; Invoke-Git $origin commit -q -m 'v5.1.0'
    & git clone -q $origin $clone 2>&1 | Out-Null
    Invoke-Git $clone config user.email 't@t'; Invoke-Git $clone config user.name 't'
    Set-Content -Path (Join-Path $origin 'VERSION') -Value '5.2.0'
    Set-Content -Path (Join-Path $origin 'docs\guide.md') -Value 'v2'
    Invoke-Git $origin add -A; Invoke-Git $origin commit -q -m 'v5.2.0'
    New-Item -ItemType Directory -Path (Join-Path $clone 'installer') -Force | Out-Null
    Copy-Item $scriptSource (Join-Path $clone 'installer\mettre-a-jour.ps1')
    Set-Content -Path (Join-Path $clone '.env') -Value 'YELEN_HTTP_PORT=8001'
    return $clone
}
function Get-Head { param([string]$Repo) (& git -C $Repo rev-parse --short HEAD).Trim() }
function Get-OriginHead { param([string]$Repo) (& git -C $Repo rev-parse --short origin/main).Trim() }
function Invoke-Update {
    param([string]$Clone, [hashtable]$Arguments = @{})
    $global:Calls.Clear()
    $before = Get-Location
    try { & (Join-Path $Clone 'installer\mettre-a-jour.ps1') @Arguments *> $null } finally { Set-Location $before }
    return $LASTEXITCODE
}
function Get-Log { param([string]$Clone) Get-Content (Join-Path $Clone 'logs\mise-a-jour.log') -Raw }

# ── 1. Mise à jour nominale ───────────────────────────────────────────────────
$clone = New-Fixture; $avant = Get-Head $clone
$global:HealthVersion = '5.2.0'
$code = Invoke-Update $clone
Assert ($code -eq 0) 'mise à jour nominale : code de retour 0'
Assert ((Get-Head $clone) -ne $avant -and (Get-Head $clone) -eq (Get-OriginHead $clone)) 'le clone est sur origin/main'
Assert ((Get-Content (Join-Path $clone 'VERSION')) -eq '5.2.0') 'VERSION 5.2.0 installée'
Assert (($global:Calls -join '|') -match 'backup-windows\.ps1\|docker compose -f .* build --progress plain\|start-local\.ps1\|docker compose -f .* ps') 'ordre : sauvegarde, build, démarrage, ps'
Assert ((Get-Log $clone) -match 'Mise à jour terminée : version 5\.2\.0') 'journal : mise à jour terminée'

# ── 2. Déjà à jour ────────────────────────────────────────────────────────────
$code = Invoke-Update $clone
Assert ($code -eq 0 -and $global:Calls.Count -eq 0) 'déjà à jour : aucune action'
Assert ((Get-Log $clone) -match 'déjà à jour \(version 5\.2\.0\)') 'journal : déjà à jour'

# ── 3. Sans sauvegarde ────────────────────────────────────────────────────────
$clone = New-Fixture
$code = Invoke-Update $clone @{ SansSauvegarde = $true }
Assert ($code -eq 0 -and -not ($global:Calls -contains 'backup-windows.ps1')) '-SansSauvegarde : sauvegarde non lancée'

# ── 4. Sauvegarde en échec : rien n'est touché ────────────────────────────────
$clone = New-Fixture; $avant = Get-Head $clone
$global:BackupExitCode = 1
$code = Invoke-Update $clone
Assert ($code -eq 1 -and (Get-Head $clone) -eq $avant) 'sauvegarde en échec : code 1, code source inchangé'
Assert (-not ($global:Calls -join '|' -match 'build')) 'sauvegarde en échec : pas de reconstruction'
$global:BackupExitCode = 0

# ── 5. Reconstruction en échec : retour au code précédent, services intacts ───
$clone = New-Fixture; $avant = Get-Head $clone
$global:BuildExitCode = 1
$code = Invoke-Update $clone
Assert ($code -eq 1 -and (Get-Head $clone) -eq $avant) 'build en échec : code 1, version précédente rétablie'
Assert (-not ($global:Calls -contains 'start-local.ps1')) 'build en échec : services non redémarrés'
$global:BuildExitCode = 0

# ── 6. Nouvelle version muette sur /health/ : reconstruction et redémarrage de l'ancienne ──
$clone = New-Fixture; $avant = Get-Head $clone
$global:HealthVersion = ''
$code = Invoke-Update $clone @{ DelaiAttente = 10 }
Assert ($code -eq 1 -and (Get-Head $clone) -eq $avant) 'santé KO : code 1, version précédente rétablie'
Assert ((@($global:Calls | Where-Object { $_ -match 'build' })).Count -eq 2 -and (@($global:Calls | Where-Object { $_ -eq 'start-local.ps1' })).Count -eq 2) 'santé KO : ancienne image reconstruite et redémarrée'
Assert ((Get-Log $clone) -match 'restaurer la sauvegarde') 'santé KO : consigne de restauration'
$global:HealthVersion = '5.2.0'

# ── 7. Modification locale : avance rapide refusée, aucune reconstruction ─────
$clone = New-Fixture; $avant = Get-Head $clone
Set-Content -Path (Join-Path $clone 'VERSION') -Value 'modifié localement'
$code = Invoke-Update $clone @{ SansSauvegarde = $true }
Assert ($code -eq 1 -and (Get-Head $clone) -eq $avant -and -not ($global:Calls -join '|' -match 'build')) 'modification locale : mise à jour annulée'
Assert ((Get-Log $clone) -match 'modifiés localement') 'modification locale : message explicite'

# ── 8. docs/ modifié (fins de ligne) : remis à l'état du dépôt, mise à jour effectuée ──
$clone = New-Fixture
Set-Content -Path (Join-Path $clone 'docs\guide.md') -Value 'v1 crlf'
$code = Invoke-Update $clone @{ SansSauvegarde = $true }
Assert ($code -eq 0 -and (Get-Content (Join-Path $clone 'docs\guide.md')) -eq 'v2') 'docs/ modifié localement : n''empêche pas la mise à jour'

Write-Host 'Tous les tests de mettre-a-jour.ps1 sont passés.'
