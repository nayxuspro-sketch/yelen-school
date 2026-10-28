#requires -Version 5.1
<##
.SYNOPSIS
    Tests de creer-environnement-test.ps1 : dépôt git réel (production fixture), docker / restauration /
    santé doublés. Exécution : pwsh -NoProfile -File installer/tests/test-creer-environnement-test.ps1
#>
$ErrorActionPreference = 'Stop'
$scriptSource = Join-Path $PSScriptRoot '..' 'creer-environnement-test.ps1'
$portSelectorSource = Join-Path $PSScriptRoot '..' 'resolve-http-port.ps1'
$hostIdSource = Join-Path $PSScriptRoot '..' 'yelen-hostid.ps1'

# ── Doublures ────────────────────────────────────────────────────────────────
$global:Calls = [System.Collections.Generic.List[string]]::new()
$global:BuildExitCode = 0
$global:RestoreExitCode = 0
$global:HealthVersion = '5.14.1'
$global:PortPublie = ''
$global:ClePrivee = ('a' * 64)
$global:ClePublique = ('b' * 64)
function docker {
    $global:Calls.Add("docker $($args -join ' ')")
    $global:LASTEXITCODE = 0
    if ($args -contains 'port') {
        if ($global:PortPublie) { $global:PortPublie } else { $global:LASTEXITCODE = 1 }
        return
    }
    if ($args -contains 'generate_licence_keys') {
        '# ── Clés Ed25519 licences P1 ──'
        "LICENCE_PRIVATE_KEY=$($global:ClePrivee)"
        ''
        "LICENCE_PUBLIC_KEY=$($global:ClePublique)"
        return
    }
    if ($args -contains 'build') { $global:LASTEXITCODE = $global:BuildExitCode }
}
function powershell.exe {
    $file = [System.IO.Path]::GetFileName($args[$args.IndexOf('-File') + 1])
    $global:Calls.Add("$file $($args[($args.IndexOf('-File') + 2)..($args.Count - 1)] -join ' ')")
    $global:LASTEXITCODE = $global:RestoreExitCode
}
function Invoke-WebRequest {
    param($Uri, [switch]$UseBasicParsing, $TimeoutSec)
    if (-not $global:HealthVersion) { throw 'connexion refusée' }
    [pscustomobject]@{ Content = ('{"status": "ok", "version": "' + $global:HealthVersion + '"}') }
}
function Start-Sleep { param($Seconds) }
function Start-Process { $global:Calls.Add("Start-Process $($args -join ' ')") }

function Assert($condition, $message) {
    if (-not $condition) { throw "ÉCHEC : $message" }
    Write-Host "  ok  $message"
}

# ── Fixture : installation de production (clone git) avec .env et sauvegardes ──
function Invoke-Git { param([string]$Repo) & git -C $Repo @args 2>&1 | Out-Null; if ($LASTEXITCODE -ne 0) { throw "git $args" } }
function New-Fixture {
    param([string]$PortProduction = '8000', [switch]$SansSauvegarde)
    $work = Join-Path ([System.IO.Path]::GetTempPath()) ('yelen-test-env-' + [guid]::NewGuid().ToString('N'))
    $prod = Join-Path $work 'YELEN-SCHOOL'
    New-Item -ItemType Directory -Path (Join-Path $prod 'installer') -Force | Out-Null
    Invoke-Git $prod init -q -b main
    Invoke-Git $prod config user.email 't@t'; Invoke-Git $prod config user.name 't'
    Set-Content -Path (Join-Path $prod 'VERSION') -Value '5.14.1'
    Set-Content -Path (Join-Path $prod 'docker-compose.client.yml') -Value 'services: {}'
    Invoke-Git $prod add -A; Invoke-Git $prod commit -q -m 'v5.14.1'
    Invoke-Git $prod remote add origin https://github.invalid/yelen-school.git
    Copy-Item $scriptSource (Join-Path $prod 'installer' 'creer-environnement-test.ps1')
    Copy-Item $portSelectorSource (Join-Path $prod 'installer' 'resolve-http-port.ps1')
    Copy-Item $hostIdSource (Join-Path $prod 'installer' 'yelen-hostid.ps1')
    $env = @(
        'SECRET_KEY=prod-secret',
        'DEBUG=False',
        'LICENSE_ENFORCEMENT=false',
        'DISABLE_HTTPS_REDIRECT=true',
        'ALLOWED_HOSTS=localhost,127.0.0.1,192.168.11.108,SERVEUR',
        'CSRF_TRUSTED_ORIGINS=https://192.168.11.108:8443,http://127.0.0.1:8000',
        'DB_PASSWORD=Yelen-secret',
        "YELEN_HTTP_PORT=$PortProduction",
        'YELEN_WEB_BIND=127.0.0.1',
        'YELEN_HTTPS=true',
        'YELEN_HTTPS_PORT=8443',
        'COMPOSE_PROFILES=https',
        'SMS_ENABLED=True',
        'SMS_HTTP_URL=http://192.168.11.50:8080/message',
        'YELEN_BACKUP_PASSPHRASE=phrase-secrete-de-sauvegarde',
        'YELEN_BACKUP_OFFSITE=D:\Sauvegardes',
        'ENSURE_ADMIN=false'
    ) -join "`n"
    [System.IO.File]::WriteAllText((Join-Path $prod '.env'), $env + "`n", [System.Text.UTF8Encoding]::new($false))
    if (-not $SansSauvegarde) {
        $backups = Join-Path $prod 'backups'
        New-Item -ItemType Directory -Path $backups -Force | Out-Null
        foreach ($nom in @('yelen_school_20261027_220000.dump.enc', 'yelen_school_20261028_090000.dump.enc')) {
            Set-Content -Path (Join-Path $backups $nom) -Value 'x'
        }
        (Get-Item (Join-Path $backups 'yelen_school_20261027_220000.dump.enc')).LastWriteTime = (Get-Date).AddDays(-1)
        (Get-Item (Join-Path $backups 'yelen_school_20261028_090000.dump.enc')).LastWriteTime = Get-Date
    }
    return $prod
}
function Get-Head { param([string]$Repo) (& git -C $Repo rev-parse HEAD).Trim() }
function Invoke-Creation {
    param([string]$Prod, [hashtable]$Arguments = @{})
    $global:Calls.Clear()
    $work = Split-Path $Prod -Parent
    $before = Get-Location
    $parametres = @{ Destination = (Join-Path $work 'YELEN-TEST'); FichierCles = (Join-Path $work 'YELEN-EDITEUR' 'cles-editeur.txt') } + $Arguments
    try { & (Join-Path $Prod 'installer' 'creer-environnement-test.ps1') @parametres *> $null } finally { Set-Location $before }
    return $LASTEXITCODE
}
function Get-Log { param([string]$Prod) Get-Content (Join-Path $Prod 'logs' 'environnement-test.log') -Raw }
function Get-EnvTest { param([string]$Prod) Get-Content (Join-Path (Split-Path $Prod -Parent) 'YELEN-TEST' '.env') -Raw }
function Get-Cles { param([string]$Prod) Get-Content (Join-Path (Split-Path $Prod -Parent) 'YELEN-EDITEUR' 'cles-editeur.txt') -Raw }

# ── 1. Première création ──────────────────────────────────────────────────────
$prod = New-Fixture
$code = Invoke-Creation $prod
$dest = Join-Path (Split-Path $prod -Parent) 'YELEN-TEST'
Assert ($code -eq 0) 'première création : code de retour 0'
Assert ((Get-Head $dest) -eq (Get-Head $prod)) 'le clone de test est à la version de la production'
Assert ((& git -C $dest remote get-url origin).Trim() -eq 'https://github.invalid/yelen-school.git') 'le clone de test pointe vers le dépôt d''origine de la production (mettre-a-jour.bat utilisable)'
$envTest = Get-EnvTest $prod
foreach ($attendu in @(
        'YELEN_ENVIRONNEMENT=test', 'YELEN_HTTP_PORT=8001', 'YELEN_WEB_BIND=127.0.0.1', 'YELEN_HTTPS=false',
        'COMPOSE_PROFILES=', 'YELEN_IMAGE=yelen-school:test', 'ALLOWED_HOSTS=localhost,127.0.0.1',
        'CSRF_TRUSTED_ORIGINS=http://localhost:8001,http://127.0.0.1:8001', 'LICENSE_ENFORCEMENT=true',
        'LICENCE_BINDING_ENABLED=true', 'LICENCE_ANTITAMPER_ENABLED=false', "LICENCE_PUBLIC_KEY=$('b' * 64)",
        'SMS_ENABLED=False', 'SMS_HTTP_URL=', 'YELEN_BACKUP_OFFSITE=', 'ENSURE_ADMIN=false',
        'SECRET_KEY=prod-secret', 'DB_PASSWORD=Yelen-secret', 'YELEN_BACKUP_PASSPHRASE=phrase-secrete-de-sauvegarde')) {
    Assert ($envTest -match "(?m)^$([regex]::Escape($attendu))\s*$") ".env de test : $attendu"
}
Assert (-not ($envTest -match '(?m)^LICENCE_PRIVATE_KEY=')) '.env de test : aucune clé privée'
$cles = Get-Cles $prod
Assert (($cles -match "(?m)^LICENCE_PRIVATE_KEY=$('a' * 64)\s*$") -and ($cles -match "(?m)^LICENCE_PUBLIC_KEY=$('b' * 64)\s*$")) 'fichier des clés : clé privée et clé publique'
$ordre = $global:Calls -join '|'
Assert ($ordre -match 'build --progress plain\|.*generate_licence_keys --format env\|.*up -d --wait db redis\|restore-windows\.ps1 .*yelen_school_20261028_090000\.dump\.enc -Yes') 'ordre : image, clés, base de test, copie de la sauvegarde la plus récente'
Assert ($ordre -match 'run --rm --no-deps -T --entrypoint python web manage.py generate_licence_keys') 'clés générées sans base de données ni entrypoint'
Assert (-not ($ordre -match 'docker compose -f [^|]* up -d\|') -and -not ($ordre -match 'up -d$')) 'web démarré par la restauration (pas de up -d global)'
Assert ((Get-Log $prod) -match 'Environnement de test prêt : http://127\.0\.0\.1:8001/accounts/login/') 'journal : environnement prêt sur le port 8001'
Assert ((Get-Log $prod) -match 'yelen_school_20261028_090000\.dump\.enc') 'journal : sauvegarde copiée nommée'
Assert ((Get-Content (Join-Path $prod '.env') -Raw) -match '(?m)^LICENSE_ENFORCEMENT=false\s*$') '.env de production inchangé'

# ── 2. Remise à niveau sans restauration : code mis à jour, clés reprises, données conservées ──
Set-Content -Path (Join-Path $prod 'VERSION') -Value '5.14.2'
Invoke-Git $prod add -A; Invoke-Git $prod commit -q -m 'v5.14.2'
$global:HealthVersion = '5.14.2'
$global:PortPublie = '127.0.0.1:8001'
$code = Invoke-Creation $prod @{ SansRestauration = $true }
Assert ($code -eq 0) 'remise à niveau : code de retour 0'
Assert ((Get-Head $dest) -eq (Get-Head $prod) -and (Get-Content (Join-Path $dest 'VERSION')) -eq '5.14.2') 'le clone de test suit la production'
$ordre = $global:Calls -join '|'
Assert (-not ($ordre -match 'generate_licence_keys') -and ((Get-EnvTest $prod) -match "(?m)^LICENCE_PUBLIC_KEY=$('b' * 64)\s*$")) 'clés de l''éditeur reprises du fichier'
Assert (-not ($ordre -match 'restore-windows') -and ($ordre -match 'build --progress plain\|docker compose -f [^|]* up -d$')) '-SansRestauration : image reconstruite, services relancés, données conservées'
Assert ((Get-EnvTest $prod) -match '(?m)^YELEN_HTTP_PORT=8001\s*$') 'port déjà publié par l''environnement de test conservé'
$global:PortPublie = ''

# ── 3. Nouvelle copie des données : sauvegarde choisie explicitement ──────────
$code = Invoke-Creation $prod @{ Sauvegarde = 'backups/yelen_school_20261027_220000.dump.enc' }
Assert ($code -eq 0 -and (($global:Calls -join '|') -match 'restore-windows\.ps1 .*yelen_school_20261027_220000\.dump\.enc -Yes')) '-Sauvegarde : fichier indiqué restauré'

# ── 4. Port de la production exclu ────────────────────────────────────────────
$prod = New-Fixture -PortProduction '8001'
$global:HealthVersion = '5.14.1'
$code = Invoke-Creation $prod
Assert ($code -eq 0 -and ((Get-EnvTest $prod) -match '(?m)^YELEN_HTTP_PORT=8002\s*$')) 'production sur 8001 : environnement de test sur 8002'
Assert ((Get-EnvTest $prod) -match '(?m)^CSRF_TRUSTED_ORIGINS=http://localhost:8002,http://127\.0\.0\.1:8002\s*$') 'origines CSRF sur le port retenu'

# ── 5. Aucune sauvegarde : refus explicite, rien n'est créé ───────────────────
$prod = New-Fixture -SansSauvegarde
$code = Invoke-Creation $prod
Assert ($code -eq 1 -and ((Get-Log $prod) -match 'Aucune sauvegarde')) 'aucune sauvegarde : code 1, message explicite'
Assert (-not (($global:Calls -join '|') -match 'build')) 'aucune sauvegarde : pas de construction'

# ── 6. Première création sans restauration : refusée ─────────────────────────
$prod = New-Fixture
$code = Invoke-Creation $prod @{ SansRestauration = $true }
Assert ($code -eq 1 -and ((Get-Log $prod) -match 'Première création')) 'première création -SansRestauration : refusée'

# ── 7. Restauration en échec ─────────────────────────────────────────────────
$prod = New-Fixture
$global:RestoreExitCode = 1
$code = Invoke-Creation $prod
Assert ($code -eq 1 -and ((Get-Log $prod) -match 'La copie de la sauvegarde a échoué')) 'restauration en échec : code 1'
$global:RestoreExitCode = 0

# ── 8. Environnement muet sur /health/ ───────────────────────────────────────
$prod = New-Fixture
$global:HealthVersion = ''
$code = Invoke-Creation $prod @{ DelaiAttente = 10 }
Assert ($code -eq 1 -and ((Get-Log $prod) -match 'ne répond pas correctement')) 'santé KO : code 1, journaux web affichés'
Assert ((($global:Calls -join '|') -match 'logs --tail 30 web')) 'santé KO : journaux du conteneur web'
$global:HealthVersion = '5.14.1'

# ── 9. Construction en échec ─────────────────────────────────────────────────
$prod = New-Fixture
$global:BuildExitCode = 1
$code = Invoke-Creation $prod
Assert ($code -eq 1 -and ((Get-Log $prod) -match 'construction de l''image a échoué') -and -not (($global:Calls -join '|') -match 'restore-windows')) 'build en échec : code 1, aucune restauration'
$global:BuildExitCode = 0

Write-Host 'Tous les tests de creer-environnement-test.ps1 sont passés.'
