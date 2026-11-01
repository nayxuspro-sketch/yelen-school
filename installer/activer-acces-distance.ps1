#requires -Version 5.1
<#
.SYNOPSIS
    Ouvre (ou ferme) l'accès à distance au portail parents par un tunnel Cloudflare.

.DESCRIPTION
    À exécuter en administrateur (activer-acces-distance.bat). Le script :
      1. vérifie cloudflared (installation par winget si absent) ;
      2. autorise le nom public dans .env : ALLOWED_HOSTS, CSRF_TRUSTED_ORIGINS
         et ACCES_DISTANCE_DOMAINE ;
      3. installe le connecteur comme service Windows avec le jeton du tunnel
         (Cloudflare Zero Trust → Réseaux → Tunnels) et le démarre ;
      4. contrôle /health/ sur le serveur, puis sur l'adresse publique.

    Aucun port n'est ouvert sur la box : le serveur établit une connexion
    sortante vers Cloudflare, qui fournit le HTTPS et le nom de domaine. La base
    reste locale et n'est jamais exposée.

    Le jeton n'est jamais écrit dans un fichier : il ne sert qu'à enregistrer le
    service. Redémarrer le serveur (demarrer-autonome.bat) après l'activation :
    le .env n'est lu qu'au démarrage.

    -Domaine : yelenschoola.nayxus.com par défaut à l'activation ; à la
    désactivation, le nom mémorisé dans .env (ACCES_DISTANCE_DOMAINE).

.EXAMPLE
    .\activer-acces-distance.bat
    .\activer-acces-distance.bat -Jeton "eyJhIjoi..."
    .\activer-acces-distance.bat -Domaine parents.mon-ecole.bf -Port 8000
    .\activer-acces-distance.bat -Desactiver
#>
[CmdletBinding()]
param(
    [string]$Domaine = '',
    [string]$Jeton = '',
    [ValidateRange(0, 65535)]
    [int]$Port = 0,
    [switch]$Desactiver
)

# ── Définitions ──────────────────────────────────────────────────────────────
$ErrorActionPreference = 'Stop'
$ServiceName = 'cloudflared'

function Get-DotEnvValue {
    param([string]$EnvFile, [string]$Name)
    if (-not (Test-Path $EnvFile)) { return '' }
    $line = Get-Content $EnvFile | Where-Object { $_ -match "^$([regex]::Escape($Name))=" } | Select-Object -First 1
    if ($null -eq $line) { return '' }
    return ($line -replace "^$([regex]::Escape($Name))=", '').Trim()
}

function Set-DotEnvValue {
    param([string]$EnvFile, [string]$Name, [string]$Value)
    $content = [System.IO.File]::ReadAllText($EnvFile, [System.Text.UTF8Encoding]::new($false))
    # [^\r\n]* : le retour chariot de la ligne est conservé tel quel (fichier CRLF sous Windows).
    $pattern = "(?m)^$([regex]::Escape($Name))=[^\r\n]*"
    $line = "$Name=$Value"
    if ([regex]::IsMatch($content, $pattern)) {
        $content = [regex]::Replace($content, $pattern, [System.Text.RegularExpressions.MatchEvaluator]{ param($match) $line })
    } else {
        $separator = if ($content.EndsWith("`n")) { '' } else { "`r`n" }
        $content = "$content$separator$line`r`n"
    }
    # UTF-8 sans BOM : un BOM rendrait la première clé du .env illisible (dotenv).
    [System.IO.File]::WriteAllText($EnvFile, $content, [System.Text.UTF8Encoding]::new($false))
}

function Remove-DotEnvKey {
    param([string]$EnvFile, [string]$Name)
    $content = [System.IO.File]::ReadAllText($EnvFile, [System.Text.UTF8Encoding]::new($false))
    $pattern = "(?m)^$([regex]::Escape($Name))=.*\r?\n?"
    $nouveau = [regex]::Replace($content, $pattern, '')
    [System.IO.File]::WriteAllText($EnvFile, $nouveau, [System.Text.UTF8Encoding]::new($false))
}

function Get-DotEnvList {
    param([string]$EnvFile, [string]$Name)
    return @((Get-DotEnvValue -EnvFile $EnvFile -Name $Name) -split ',' |
        ForEach-Object { $_.Trim() } | Where-Object { $_ })
}

function Add-DotEnvList {
    param([string]$EnvFile, [string]$Name, [string]$Value)
    $items = @(Get-DotEnvList -EnvFile $EnvFile -Name $Name)
    if ($items -contains $Value) { return $false }
    Set-DotEnvValue -EnvFile $EnvFile -Name $Name -Value ((@($items) + $Value) -join ',')
    return $true
}

function Remove-DotEnvList {
    param([string]$EnvFile, [string]$Name, [string]$Value)
    $items = @(Get-DotEnvList -EnvFile $EnvFile -Name $Name)
    $restants = @($items | Where-Object { $_ -ne $Value })
    if ($restants.Count -eq $items.Count) { return $false }
    Set-DotEnvValue -EnvFile $EnvFile -Name $Name -Value ($restants -join ',')
    return $true
}

function Write-AccesLog {
    param([string]$LogFile, [string]$Message)
    Add-Content -Path $LogFile -Value "$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') $Message" -Encoding UTF8
}

function Assert-Administrateur {
    $principal = New-Object Security.Principal.WindowsPrincipal([Security.Principal.WindowsIdentity]::GetCurrent())
    if (-not $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
        throw 'Ce script doit être exécuté en tant qu''administrateur (installation du service Windows cloudflared).'
    }
}

function Assert-NomPublic {
    param([string]$Nom)
    if ($Nom -notmatch '^([a-z0-9]([a-z0-9-]*[a-z0-9])?\.)+[a-z]{2,}$') {
        throw "Nom public invalide : « $Nom ». Attendu : un nom complet en minuscules, par exemple yelenschoola.nayxus.com."
    }
}

function Resolve-PortApplication {
    param([string]$EnvFile, [int]$Port)
    if ($Port -gt 0) { return $Port }
    # YELEN_HTTP_PORT : installation Docker ; PORT : mode autonome (les deux .env coexistent).
    foreach ($cle in @('YELEN_HTTP_PORT', 'PORT')) {
        $valeur = Get-DotEnvValue -EnvFile $EnvFile -Name $cle
        if ($valeur -match '^\d+$') { return [int]$valeur }
    }
    return 8000
}

function Resolve-ModeDeploiement {
    # « docker » si le conteneur web tourne (installation Docker, C:\YELEN-SCHOOL) ; sinon mode autonome
    # (Waitress lancé par demarrer-autonome.bat). Le dépôt est le même : seul le conteneur les distingue.
    param([string]$Root)
    if (-not (Get-Command 'docker' -ErrorAction SilentlyContinue)) { return 'autonome' }
    $compose = Join-Path $Root 'docker-compose.client.yml'
    if (-not (Test-Path $compose)) { return 'autonome' }
    $ErrorActionPreference = 'Continue'
    $conteneur = ''
    try { $conteneur = "$(& docker compose -f $compose ps -q web 2>$null)".Trim() } catch { $conteneur = '' }
    if ($conteneur) { return 'docker' }
    return 'autonome'
}

function Get-InstructionRedemarrage {
    # Le mode autonome relit .env à chaque démarrage ; Docker seulement à la création des conteneurs.
    param([string]$Mode)
    if ($Mode -eq 'docker') {
        return 'fermez l''application puis double-cliquez sur demarrer.bat (les conteneurs sont recréés et relisent .env).'
    }
    return 'fermez la fenêtre « YELEN SCHOOL - Serveur », puis double-cliquez sur demarrer-autonome.bat.'
}

function Resolve-Cloudflared {
    # Chemin de cloudflared ; installation par winget si le poste ne l'a pas encore.
    $commande = Get-Command 'cloudflared' -ErrorAction SilentlyContinue
    if ($commande) { return $commande.Source }
    if (Get-Command 'winget' -ErrorAction SilentlyContinue) {
        Write-Host '        cloudflared absent : installation par winget...' -ForegroundColor Gray
        $null = Invoke-NativeQuiet { & winget install --id Cloudflare.cloudflared -e --silent --accept-package-agreements --accept-source-agreements }
        $commande = Get-Command 'cloudflared' -ErrorAction SilentlyContinue
        if ($commande) { return $commande.Source }
    }
    $candidats = @()
    if ($env:ProgramFiles) { $candidats += (Join-Path $env:ProgramFiles 'cloudflared\cloudflared.exe') }
    if (${env:ProgramFiles(x86)}) { $candidats += (Join-Path ${env:ProgramFiles(x86)} 'cloudflared\cloudflared.exe') }
    foreach ($candidat in $candidats) {
        if (Test-Path $candidat) { return $candidat }
    }
    throw ("cloudflared est introuvable. Installez-le une fois avec :`r`n" +
           "  winget install --id Cloudflare.cloudflared -e`r`n" +
           "ou téléchargez cloudflared-windows-amd64.msi sur https://github.com/cloudflare/cloudflared/releases/latest")
}

function Invoke-NativeQuiet {
    # Exécute une commande native sans afficher sa sortie et retourne son code de retour.
    # Sous $ErrorActionPreference = 'Stop', la sortie d'erreur redirigée d'une commande
    # native devient une exception : elle est ignorée ici.
    param([Parameter(Mandatory = $true)][scriptblock]$Command)
    $ErrorActionPreference = 'Continue'
    & $Command *> $null
    return $LASTEXITCODE
}

function Invoke-Cloudflared {
    # Appel à cloudflared (isolé pour les tests) : retourne le code de retour.
    param([string]$Cloudflared, [string[]]$Arguments)
    $ErrorActionPreference = 'Continue'
    & $Cloudflared @Arguments *> $null
    return $LASTEXITCODE
}

function Test-PointDeSante {
    # Retourne 'ok' (YELEN répond), 'autre' (un autre site répond pour ce nom : tunnel non relié ou
    # enregistrement *.domaine générique) ou 'muet' (rien ne répond).
    param([string]$Url, [int]$Tentatives = 1, [int]$AttenteSecondes = 5, [switch]$YelenSeulement)
    $dernier = 'muet'
    for ($essai = 1; $essai -le $Tentatives; $essai++) {
        try {
            $reponse = Invoke-WebRequest -Uri $Url -UseBasicParsing -TimeoutSec 10 -ErrorAction Stop
            if ($reponse.StatusCode -eq 200) {
                if (-not $YelenSeulement) { return 'ok' }
                # /health/ de YELEN renvoie {"status": "ok", "version": ...} ; une page HTML ne compte pas.
                if ("$($reponse.Content)" -match '"status"') { return 'ok' }
                $dernier = 'autre'
            }
        } catch {
            # Adresse pas encore joignable : nouvel essai.
        }
        if ($essai -lt $Tentatives) { Start-Sleep -Seconds $AttenteSecondes }
    }
    return $dernier
}

function Invoke-AccesDistance {
    param(
        [Parameter(Mandatory = $true)][string]$Root,
        [string]$Domaine = '',
        [string]$Jeton = '',
        [int]$Port = 0,
        [switch]$Desactiver
    )

    $EnvFile = Join-Path $Root '.env'

    Assert-Administrateur
    if (-not (Test-Path $EnvFile)) {
        throw '.env est introuvable. Lancez d''abord l''installation (guide de déploiement, §2 et §3.6).'
    }
    $LogFile = Join-Path (Join-Path $Root 'logs') 'acces-distance.log'
    New-Item -ItemType Directory -Path (Join-Path $Root 'logs') -Force | Out-Null
    $Mode = Resolve-ModeDeploiement -Root $Root

    if (-not $Domaine) {
        # Désactivation : reprendre le nom mémorisé par l'activation ; sinon, nom de l'établissement.
        if ($Desactiver) { $Domaine = Get-DotEnvValue -EnvFile $EnvFile -Name 'ACCES_DISTANCE_DOMAINE' }
        else { $Domaine = 'yelenschoola.nayxus.com' }
    }
    if (-not $Domaine) {
        throw 'Précisez le nom public avec -Domaine : aucun accès à distance n''est mémorisé dans .env.'
    }

    if ($Desactiver) {
        Write-Host '[1/3] Arrêt et suppression du service cloudflared...' -ForegroundColor Cyan
        $service = Get-Service -Name $ServiceName -ErrorAction SilentlyContinue
        if ($service) {
            Stop-Service -Name $ServiceName -Force -ErrorAction SilentlyContinue
            $commande = Get-Command 'cloudflared' -ErrorAction SilentlyContinue
            if ($commande) {
                $null = Invoke-Cloudflared -Cloudflared $commande.Source -Arguments @('service', 'uninstall')
            } else {
                $null = Invoke-NativeQuiet { & sc.exe delete $ServiceName }
            }
        }

        Write-Host '[2/3] Retrait du nom public de .env...' -ForegroundColor Cyan
        $null = Remove-DotEnvList -EnvFile $EnvFile -Name 'ALLOWED_HOSTS' -Value $Domaine
        $null = Remove-DotEnvList -EnvFile $EnvFile -Name 'CSRF_TRUSTED_ORIGINS' -Value "https://$Domaine"
        Remove-DotEnvKey -EnvFile $EnvFile -Name 'ACCES_DISTANCE_DOMAINE'

        Write-Host '[3/3] Terminé.' -ForegroundColor Cyan
        Write-AccesLog -LogFile $LogFile -Message "Accès à distance désactivé ($Domaine)."
        Write-Host ''
        Write-Host "Accès à distance fermé. $Domaine n'est plus autorisé par le serveur." -ForegroundColor Green
        Write-Host "Supprimez au besoin le nom d'hôte public du tunnel dans le tableau de bord Cloudflare."
        Write-Host "Pour appliquer le .env : $(Get-InstructionRedemarrage -Mode $Mode)"
        return
    }

    Assert-NomPublic -Nom $Domaine
    $Port = Resolve-PortApplication -EnvFile $EnvFile -Port $Port

    if (-not $Jeton) {
        Write-Host ''
        Write-Host 'Jeton du tunnel : Cloudflare Zero Trust → Réseaux → Tunnels → votre tunnel → Configurer.' -ForegroundColor Yellow
        $Jeton = Read-Host -Prompt 'Collez le jeton du tunnel (il commence par eyJ)'
    }
    $Jeton = "$Jeton".Trim().Trim('"')
    if ($Jeton.Length -lt 40) {
        throw 'Jeton absent ou invalide. Copiez la valeur complète de la commande « cloudflared service install ... » affichée par Cloudflare.'
    }

    Write-Host '[1/5] Vérification de cloudflared...' -ForegroundColor Cyan
    $cloudflared = Resolve-Cloudflared
    Write-Host "        $cloudflared" -ForegroundColor Gray

    Write-Host '[2/5] Autorisation du nom public dans .env...' -ForegroundColor Cyan
    $ajoutHost = Add-DotEnvList -EnvFile $EnvFile -Name 'ALLOWED_HOSTS' -Value $Domaine
    $ajoutCsrf = Add-DotEnvList -EnvFile $EnvFile -Name 'CSRF_TRUSTED_ORIGINS' -Value "https://$Domaine"
    Set-DotEnvValue -EnvFile $EnvFile -Name 'ACCES_DISTANCE_DOMAINE' -Value $Domaine
    if ($ajoutHost) { Write-Host "        ALLOWED_HOSTS : $Domaine ajouté." -ForegroundColor Gray }
    else { Write-Host '        ALLOWED_HOSTS : déjà autorisé.' -ForegroundColor Gray }
    if ($ajoutCsrf) { Write-Host "        CSRF_TRUSTED_ORIGINS : https://$Domaine ajouté." -ForegroundColor Gray }
    else { Write-Host '        CSRF_TRUSTED_ORIGINS : déjà autorisé.' -ForegroundColor Gray }

    Write-Host '[3/5] Installation du service cloudflared...' -ForegroundColor Cyan
    $existant = Get-Service -Name $ServiceName -ErrorAction SilentlyContinue
    if ($existant) {
        Stop-Service -Name $ServiceName -Force -ErrorAction SilentlyContinue
        $null = Invoke-Cloudflared -Cloudflared $cloudflared -Arguments @('service', 'uninstall')
    }
    $code = Invoke-Cloudflared -Cloudflared $cloudflared -Arguments @('service', 'install', $Jeton)
    if ($code -ne 0) {
        throw "L'installation du service a échoué (code $code). Vérifiez que le jeton vient bien de la page « Configurer » du tunnel."
    }
    $service = Get-Service -Name $ServiceName -ErrorAction SilentlyContinue
    if (-not $service) {
        throw 'Le service cloudflared est introuvable après l''installation. Redémarrez Windows puis relancez ce script.'
    }
    if ($service.Status -ne 'Running') { Start-Service -Name $ServiceName -ErrorAction SilentlyContinue }
    Start-Sleep -Seconds 3

    Write-Host '[4/5] Contrôle du serveur local...' -ForegroundColor Cyan
    $adresseLocale = "http://127.0.0.1:$Port/health/"
    if ((Test-PointDeSante -Url $adresseLocale -Tentatives 2 -AttenteSecondes 2 -YelenSeulement) -eq 'ok') {
        Write-Host "        Serveur joignable ($adresseLocale)." -ForegroundColor Green
    } else {
        Write-Host "        Serveur muet sur $adresseLocale : démarrez-le (demarrer-autonome.bat)." -ForegroundColor Yellow
        Write-Host '        Le tunnel fonctionnera dès que le serveur répondra.' -ForegroundColor Yellow
    }

    Write-Host '[5/5] Contrôle de l''adresse publique (jusqu''à 60 s)...' -ForegroundColor Cyan
    $adressePublique = "https://$Domaine/health/"
    $etat = Test-PointDeSante -Url $adressePublique -Tentatives 12 -AttenteSecondes 5 -YelenSeulement
    if ($etat -eq 'ok') {
        Write-Host "        [OK] $adressePublique répond (YELEN SCHOOL)." -ForegroundColor Green
    } elseif ($etat -eq 'autre') {
        Write-Host "        $Domaine répond, mais ce n'est PAS YELEN SCHOOL : un autre site occupe ce nom." -ForegroundColor Red
        Write-Host "        Le tunnel n'est donc pas relié à ce nom d'hôte. Dans Cloudflare Zero Trust :" -ForegroundColor Yellow
        Write-Host "          - Tunnels -> votre tunnel -> Nom d'hôte public : $Domaine -> HTTP localhost:$Port" -ForegroundColor Yellow
        Write-Host "          - puis redémarrer le serveur (le .env n'est lu qu'au démarrage)." -ForegroundColor Yellow
        Write-Host '        Un enregistrement générique *.nayxus.com explique souvent cette page générique.' -ForegroundColor Yellow
    } else {
        Write-Host "        $adressePublique ne répond pas encore. Vérifiez dans le tableau de bord :" -ForegroundColor Yellow
        Write-Host "          - Nom d'hôte public : $Domaine" -ForegroundColor Yellow
        Write-Host "          - Service           : http://localhost:$Port" -ForegroundColor Yellow
        Write-Host '          - La propagation DNS peut prendre quelques minutes.' -ForegroundColor Yellow
    }

    Write-AccesLog -LogFile $LogFile -Message "Accès à distance activé : https://$Domaine -> http://localhost:$Port."
    Write-Host ''
    Write-Host '============================================================' -ForegroundColor Green
    Write-Host "  Accès à distance : https://$Domaine/" -ForegroundColor Green
    Write-Host '============================================================' -ForegroundColor Green
    Write-Host "  Nom d'hôte public : $Domaine"
    Write-Host "  Service local     : http://localhost:$Port"
    Write-Host ''
    Write-Host 'IMPORTANT : redémarrez le serveur pour appliquer le .env' -ForegroundColor Yellow
    Write-Host "  $(Get-InstructionRedemarrage -Mode $Mode)"
    Write-Host ''
    Write-Host 'Communiquez ensuite l''adresse aux parents : ils se connectent avec leur numéro de'
    Write-Host 'téléphone et installent l''application depuis le navigateur (guide, §19.1 et §19.7).'
}

# ── Exécution ────────────────────────────────────────────────────────────────
$Root = [System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))
Invoke-AccesDistance -Root $Root -Domaine $Domaine -Jeton $Jeton -Port $Port -Desactiver:$Desactiver
