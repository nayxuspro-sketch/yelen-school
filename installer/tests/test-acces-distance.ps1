#requires -Version 5.1
<#
.SYNOPSIS
    Tests de activer-acces-distance.ps1 : cloudflared, service Windows et point de santé doublés.
    Exécution : pwsh -NoProfile -File installer/tests/test-acces-distance.ps1
    (Windows PowerShell 5.1 ou PowerShell 7 ; aucun réseau, aucun service requis.)
#>
$ErrorActionPreference = 'Stop'

# Fonctions du script (tout ce qui va du marqueur « Définitions » au marqueur « Exécution »), sans son en-tête.
$scriptPath = Join-Path (Join-Path $PSScriptRoot '..') 'activer-acces-distance.ps1'
$script = [System.IO.File]::ReadAllText($scriptPath, [System.Text.UTF8Encoding]::new($false))
$debut = $script.IndexOf('# ── Définitions')
$fin = $script.IndexOf('# ── Exécution')
if ($debut -lt 0 -or $fin -lt 0) { throw 'Marqueurs du script introuvables.' }

$work = Join-Path ([System.IO.Path]::GetTempPath()) ('yelen-distance-' + [guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Path $work -Force | Out-Null
$defsFile = Join-Path $work 'defs.ps1'
[System.IO.File]::WriteAllText($defsFile, $script.Substring($debut, $fin - $debut), [System.Text.UTF8Encoding]::new($true))
. $defsFile

$EnvFile = Join-Path $work '.env'

# ── Doublures ────────────────────────────────────────────────────────────────
$script:Calls = [System.Collections.Generic.List[string]]::new()
$script:ServiceExiste = $false
$script:ServiceEtat = 'Stopped'
$script:SanteLocale = $true
$script:SantePublique = $true
$script:ReponseJeton = 'eyJhIjoiZXhhbXBsZSJ9' + ('x' * 40)

function Assert-Administrateur { }
function Start-Sleep { param($Seconds) }
function Get-Service {
    param([string]$Name, $ErrorAction)
    if ($script:ServiceExiste) { [pscustomobject]@{ Name = $Name; Status = $script:ServiceEtat } }
}
function Start-Service {
    param([string]$Name, $ErrorAction)
    $script:Calls.Add("Start-Service $Name")
    $script:ServiceEtat = 'Running'
}
function Stop-Service {
    param([string]$Name, [switch]$Force, $ErrorAction)
    $script:Calls.Add("Stop-Service $Name")
    $script:ServiceEtat = 'Stopped'
}
function Get-Command {
    param([string]$Name, $ErrorAction)
    if ($Name -eq 'cloudflared') { [pscustomobject]@{ Name = 'cloudflared'; Source = '/opt/cloudflared' } }
    if ($Name -eq 'docker') { [pscustomobject]@{ Name = 'docker'; Source = '/usr/bin/docker' } }
}
function Invoke-Cloudflared {
    param([string]$Cloudflared, [string[]]$Arguments)
    $script:Calls.Add("cloudflared $($Arguments -join ' ')")
    if (@($Arguments) -contains 'install') { $script:ServiceExiste = $true; $script:ServiceEtat = 'Running' }
    if (@($Arguments) -contains 'uninstall') { $script:ServiceEtat = 'Stopped' }
    return 0
}
function Invoke-WebRequest {
    param($Uri, [switch]$UseBasicParsing, $TimeoutSec, $ErrorAction)
    $script:Calls.Add("GET $Uri")
    $joignable = if ($Uri -like 'http://127.0.0.1*') { $script:SanteLocale } else { $script:SantePublique }
    if (-not $joignable) { throw 'connexion refusée' }
    $corps = if ($Uri -like 'http://127.0.0.1*') { $script:CorpsLocal } else { $script:CorpsPublic }
    [pscustomobject]@{ StatusCode = 200; Content = $corps }
}
$script:CorpsLocal = '{"status": "ok", "version": "5.46.2"}'
$script:CorpsPublic = '{"status": "ok", "version": "5.46.2"}'
function Read-Host { param($Prompt) $script:ReponseJeton }
function docker { param([Parameter(ValueFromRemainingArguments = $true)]$Arguments) if ($script:ConteneurWeb) { $script:ConteneurWeb } }
$script:ConteneurWeb = ''
$script:Sortie = [System.Collections.Generic.List[string]]::new()
function Write-Host {
    # Les messages sont conservés (vérification des consignes de redémarrage) et affichés.
    param([Parameter(Position = 0)]$Object, [string]$ForegroundColor, [switch]$NoNewline)
    if ($null -ne $Object) {
        $script:Sortie.Add("$Object")
        [Console]::WriteLine("$Object")
    }
}

# ── Utilitaires ──────────────────────────────────────────────────────────────
function Assert($condition, $message) {
    if (-not $condition) { throw "ÉCHEC : $message" }
    Write-Host "  ok  $message"
}
function Get-EnvLine($name) { [System.IO.File]::ReadAllLines($EnvFile) | Where-Object { $_ -like "$name=*" } }
function Set-EnvContent($content) { [System.IO.File]::WriteAllText($EnvFile, $content, [System.Text.UTF8Encoding]::new($false)) }

$jeton = 'a' * 60

# ── 1. Activation ────────────────────────────────────────────────────────────
Write-Host 'Activation'
Set-EnvContent "SECRET_KEY=abc`nALLOWED_HOSTS=localhost,127.0.0.1,192.168.1.10`nCSRF_TRUSTED_ORIGINS=http://localhost:8000`nPORT=8080`n"
Invoke-AccesDistance -Root $work -Domaine 'yelenschoola.nayxus.com' -Jeton $jeton 6>$null

$hotes = (Get-EnvLine 'ALLOWED_HOSTS') -join ''
Assert ($hotes -match 'yelenschoola\.nayxus\.com') 'le nom public est autorisé dans ALLOWED_HOSTS'
Assert ($hotes -match '192\.168\.1\.10') 'les hôtes existants sont conservés'
$csrf = (Get-EnvLine 'CSRF_TRUSTED_ORIGINS') -join ''
Assert ($csrf -match 'https://yelenschoola\.nayxus\.com') "l'origine HTTPS est autorisée (CSRF)"
Assert ($csrf -match 'http://localhost:8000') 'les origines existantes sont conservées'
Assert (((Get-EnvLine 'ACCES_DISTANCE_DOMAINE') -join '') -eq 'ACCES_DISTANCE_DOMAINE=yelenschoola.nayxus.com') 'le nom public est mémorisé'
Assert ((($script:Calls -join "`n") -match "cloudflared service install $jeton")) 'le service est installé avec le jeton'
Assert ($script:Calls -contains 'GET http://127.0.0.1:8080/health/') 'le port est lu dans le .env (PORT=8080)'
Assert ($script:Calls -contains 'GET https://yelenschoola.nayxus.com/health/') "l'adresse publique est contrôlée"
Assert (Test-Path (Join-Path (Join-Path $work 'logs') 'acces-distance.log')) 'le journal est écrit'

# ── 2. Idempotence ───────────────────────────────────────────────────────────
Write-Host 'Activation répétée'
$script:Calls.Clear()
Invoke-AccesDistance -Root $work -Domaine 'yelenschoola.nayxus.com' -Jeton ('b' * 60) 6>$null
$hotes = (Get-EnvLine 'ALLOWED_HOSTS') -join ''
Assert (([regex]::Matches($hotes, 'yelenschoola\.nayxus\.com')).Count -eq 1) 'ALLOWED_HOSTS ne contient pas de doublon'
Assert ((($script:Calls -join "`n") -match 'cloudflared service uninstall')) 'le service existant est remplacé, pas dupliqué'

# ── 3. Jeton demandé, jeton refusé ───────────────────────────────────────────
Write-Host 'Jeton'
$script:Calls.Clear()
Invoke-AccesDistance -Root $work -Domaine 'yelenschoola.nayxus.com' 6>$null
Assert ((($script:Calls -join "`n") -match 'cloudflared service install eyJ')) 'le jeton saisi est utilisé'
$script:ReponseJeton = 'court'
$echec = $false
try { Invoke-AccesDistance -Root $work -Domaine 'yelenschoola.nayxus.com' 6>$null } catch { $echec = $true }
Assert $echec 'un jeton trop court est refusé'

# ── 4. Nom public invalide, .env absent ──────────────────────────────────────
Write-Host 'Contrôles'
$echec = $false
try { Invoke-AccesDistance -Root $work -Domaine 'pas un domaine' -Jeton $jeton 6>$null } catch { $echec = $true }
Assert $echec 'un nom public invalide est refusé'
$vide = Join-Path $work 'vide'
New-Item -ItemType Directory -Path $vide -Force | Out-Null
$echec = $false
try { Invoke-AccesDistance -Root $vide -Domaine 'ecole.test' -Jeton $jeton 6>$null } catch { $echec = $true }
Assert $echec 'un .env absent est signalé'
Assert (-not (Test-Path (Join-Path $vide 'logs'))) 'aucun dossier créé hors du projet'

# ── 5. Désactivation ─────────────────────────────────────────────────────────
Write-Host 'Désactivation'
$script:Calls.Clear()
Invoke-AccesDistance -Root $work -Desactiver 6>$null   # nom public relu dans .env
$hotes = (Get-EnvLine 'ALLOWED_HOSTS') -join ''
Assert (-not ($hotes -match 'nayxus')) 'le nom public est retiré de ALLOWED_HOSTS'
Assert ($hotes -match '192\.168\.1\.10') 'les autres hôtes restent autorisés'
$csrf = (Get-EnvLine 'CSRF_TRUSTED_ORIGINS') -join ''
Assert (-not ($csrf -match 'nayxus')) "l'origine publique est retirée"
Assert (-not (Get-EnvLine 'ACCES_DISTANCE_DOMAINE')) 'la mémorisation du nom public est supprimée'
Assert ($script:Calls -contains 'Stop-Service cloudflared') 'le service est arrêté'
Assert ((($script:Calls -join "`n") -match 'cloudflared service uninstall')) 'le service est supprimé'

# ── 6. Installation Docker (conteneur web) ───────────────────────────────────
Write-Host 'Installation Docker'
Set-EnvContent "SECRET_KEY=abc`nYELEN_HTTP_PORT=8081`nALLOWED_HOSTS=localhost`nCSRF_TRUSTED_ORIGINS=http://localhost:8081`n"
Set-Content -Path (Join-Path $work 'docker-compose.client.yml') -Value 'services: {}'   # installation Docker
$script:ConteneurWeb = 'a1b2c3'
$script:Calls.Clear()
$script:Sortie.Clear()
Invoke-AccesDistance -Root $work -Domaine 'yelenschoola.nayxus.com' -Jeton $jeton 6>$null
Assert ($script:Calls -contains 'GET http://127.0.0.1:8081/health/') 'le port Docker est lu dans YELEN_HTTP_PORT'
$messages = $script:Sortie -join "`n"
Assert ($messages -match 'demarrage\.bat') 'le redémarrage Docker passe par demarrage.bat (conteneurs recréés)'
Assert (-not ($messages -match 'demarrer-autonome\.bat')) 'aucune consigne autonome pour une installation Docker'

Write-Host 'Mode autonome'
$script:ConteneurWeb = ''
Remove-Item -Path (Join-Path $work 'docker-compose.client.yml') -Force
$script:Sortie.Clear()
Invoke-AccesDistance -Root $work -Domaine 'yelenschoola.nayxus.com' -Jeton $jeton 6>$null
$messages = $script:Sortie -join "`n"
Assert ($messages -match 'demarrer-autonome\.bat') 'le mode autonome redémarre par demarrer-autonome.bat'
$script:ConteneurWeb = ''

# ── 7. Un autre site répond pour le nom public ───────────────────────────────
Write-Host 'Autre site sur le nom public'
$script:CorpsPublic = '<!DOCTYPE html><html><body>GAME OVER</body></html>'
$script:Sortie.Clear()
Invoke-AccesDistance -Root $work -Domaine 'yelenschoola.nayxus.com' -Jeton $jeton 6>$null
$messages = $script:Sortie -join "`n"
Assert ($messages -match "ce n'est PAS YELEN SCHOOL") 'une page étrangère est signalée comme telle'
Assert ($messages -match 'Nom d.hôte public') 'la consigne du tunnel est donnée'
Assert (-not ($messages -match '\[OK\]')) 'aucun faux succès lorsque le nom public sert un autre site'

Write-Host 'Port local occupé par autre chose'
$script:CorpsPublic = '{"status": "ok", "version": "5.46.2"}'
$script:CorpsLocal = '<html>autre application</html>'
$script:Sortie.Clear()
Invoke-AccesDistance -Root $work -Domaine 'yelenschoola.nayxus.com' -Jeton $jeton 6>$null
Assert ((($script:Sortie -join "`n") -match 'Serveur muet')) 'un port local servi par autre chose est signalé'
$script:CorpsLocal = '{"status": "ok", "version": "5.46.2"}'

# ── 8. .env seulement (tunnel assuré autrement : Tailscale Funnel) ───────────
Write-Host '.env seulement'
Set-EnvContent "SECRET_KEY=abc`nALLOWED_HOSTS=localhost`nCSRF_TRUSTED_ORIGINS=http://localhost:8000`nPORT=8000`n"
$script:Calls.Clear()
$script:Sortie.Clear()
Invoke-AccesDistance -Root $work -Domaine 'bureau-nkqmf8l.tail1234.ts.net' -EnvSeulement 6>$null
$hotes = (Get-EnvLine 'ALLOWED_HOSTS') -join ''
$csrf = (Get-EnvLine 'CSRF_TRUSTED_ORIGINS') -join ''
Assert ($hotes -match 'bureau-nkqmf8l\.tail1234\.ts\.net') 'le nom public est autorisé'
Assert ($csrf -match 'https://bureau-nkqmf8l\.tail1234\.ts\.net') "l'origine HTTPS est autorisée"
Assert (-not ($script:Calls -join "`n" -match 'cloudflared')) 'aucun service Cloudflare installé'
Assert (-not ($script:Calls -join "`n" -match 'GET ')) 'aucun contrôle réseau effectué'
Assert ((($script:Sortie -join "`n")) -match 'aucun service Cloudflare') 'le mode est annoncé'

# ── Nettoyage ────────────────────────────────────────────────────────────────
Remove-Item -Recurse -Force $work
Write-Host 'Tous les tests sont passés.'
