#requires -Version 5.1
<##
.SYNOPSIS
    Crée ou rafraîchit un environnement de test isolé à partir de cette installation Docker.
.DESCRIPTION
    À lancer depuis le dossier de production (creer-environnement-test.bat). Dans le dossier de
    destination (par défaut YELEN-TEST à côté du dossier de production) :
      - même version du code (clone git local de ce dossier, remis à niveau s'il existe déjà) ;
      - .env dérivé de celui de la production : autre port HTTP (127.0.0.1 seulement, sans HTTPS),
        image Docker, base et médias distincts, SMS, paiements mobiles et sauvegarde distante
        désactivés, bandeau « ENVIRONNEMENT DE TEST » sur toutes les pages ;
      - contrôle des licences ACTIF (LICENSE_ENFORCEMENT=true, LICENCE_BINDING_ENABLED=true) avec la
        clé publique de l'éditeur : la paire de clés est créée une seule fois dans -FichierCles
        (la clé privée n'est jamais copiée dans un .env ni affichée) ;
      - copie de la dernière sauvegarde de la production (base + médias), sauf -SansRestauration.
    La production (dossier courant, conteneurs, volumes, .env) n'est jamais modifiée.
    Journal : logs\environnement-test.log.
.PARAMETER Destination
    Dossier de l'environnement de test (défaut : <dossier parent>\YELEN-TEST).
.PARAMETER Port
    Port HTTP souhaité (défaut 8001 ; un port libre de la plage 8000-8005 est retenu s'il est occupé).
.PARAMETER Sauvegarde
    Sauvegarde .dump ou .dump.enc à copier (défaut : la plus récente de backups\).
.PARAMETER SansRestauration
    Conserver les données déjà présentes dans l'environnement de test (code et image remis à niveau).
.PARAMETER FichierCles
    Fichier des clés de l'éditeur (défaut : <dossier parent>\YELEN-EDITEUR\cles-editeur.txt).
.PARAMETER OuvrirNavigateur
    Ouvrir la page de connexion de l'environnement de test à la fin.
.PARAMETER DelaiAttente
    Secondes accordées à l'environnement de test pour répondre sur /health/ (migrations comprises).
#>

[CmdletBinding()]
param(
    [string]$Destination = '',
    [ValidateRange(1, 65535)]
    [int]$Port = 8001,
    [string]$Sauvegarde = '',
    [switch]$SansRestauration,
    [string]$FichierCles = '',
    [switch]$OuvrirNavigateur,
    [ValidateRange(10, 3600)]
    [int]$DelaiAttente = 300
)

$ErrorActionPreference = 'Stop'
$Root = [System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))
$EnvFile = Join-Path $Root '.env'
$Parent = Split-Path $Root -Parent
if ([string]::IsNullOrWhiteSpace($Destination)) { $Destination = Join-Path $Parent 'YELEN-TEST' }
$Destination = [System.IO.Path]::GetFullPath($Destination)
if ([string]::IsNullOrWhiteSpace($FichierCles)) { $FichierCles = Join-Path $Parent 'YELEN-EDITEUR\cles-editeur.txt' }
$DestComposeFile = Join-Path $Destination 'docker-compose.client.yml'
$DestEnvFile = Join-Path $Destination '.env'
$PortSelectorScript = Join-Path $PSScriptRoot 'resolve-http-port.ps1'
$HostIdScript = Join-Path $PSScriptRoot 'yelen-hostid.ps1'
$LogDirectory = Join-Path $Root 'logs'
$LogFile = Join-Path $LogDirectory 'environnement-test.log'

function Write-Log {
    param([string]$Message)
    $line = "$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') $Message"
    Add-Content -Path $LogFile -Value $line -Encoding UTF8
    Write-Host $line
}

function Invoke-Native {
    # Exécute une commande native en affichant sa sortie et ne retourne que son code de retour
    # (sous 'Stop', Windows PowerShell transformerait la progression écrite sur stderr en erreur).
    # Les commandes docker affichant une progression interactive reçoivent --progress plain.
    param([Parameter(Mandatory = $true)][scriptblock]$Command)
    $ErrorActionPreference = 'Continue'
    & $Command | Out-Host
    $code = $LASTEXITCODE
    $ErrorActionPreference = 'Stop'
    return $code
}

function Invoke-NativeQuiet {
    # Exécute une commande native sans afficher sa sortie et retourne son code de retour.
    param([Parameter(Mandatory = $true)][scriptblock]$Command)
    $ErrorActionPreference = 'Continue'
    & $Command *> $null
    $code = $LASTEXITCODE
    $ErrorActionPreference = 'Stop'
    return $code
}

function Get-NativeLines {
    # Sortie standard d'une commande native (tableau de lignes) ; $null si elle échoue.
    param([Parameter(Mandatory = $true)][scriptblock]$Command)
    $ErrorActionPreference = 'Continue'
    $output = @(& $Command 2>$null | ForEach-Object { [string]$_ })
    $code = $LASTEXITCODE
    $ErrorActionPreference = 'Stop'
    if ($code -ne 0) { return $null }
    return $output
}

function Get-GitOutput {
    param([string[]]$Arguments)
    $lines = Get-NativeLines { & git @Arguments }
    if ($null -eq $lines) { return $null }
    return ($lines -join "`n").Trim()
}

function Get-DotEnvValue {
    param([string]$Path, [string]$Name)
    if (-not (Test-Path $Path)) { return '' }
    $line = Get-Content $Path | Where-Object { $_ -match "^$([regex]::Escape($Name))=" } | Select-Object -First 1
    if ($null -eq $line) { return '' }
    return ($line -replace "^$([regex]::Escape($Name))=", '').Trim()
}

function Set-EnvLine {
    # Remplace la ligne NOM=… du contenu .env (ou l'ajoute à la fin) et retourne le contenu.
    param([string]$Content, [string]$Name, [string]$Value)
    $escapedName = [regex]::Escape($Name)
    $line = "$Name=$Value"
    if ([regex]::IsMatch($Content, "(?m)^$escapedName=.*$")) {
        return [regex]::Replace($Content, "(?m)^$escapedName=.*$",
            [System.Text.RegularExpressions.MatchEvaluator]{ param($match) $line })
    }
    if ($Content.Length -gt 0 -and -not $Content.EndsWith("`n")) { $Content += "`r`n" }
    return $Content + $line + "`r`n"
}

function Get-CleDepuisFichier {
    param([string]$Path, [string]$Name)
    $line = Get-Content $Path | Where-Object { $_ -match "^$Name=[0-9A-Fa-f]+\s*$" } | Select-Object -First 1
    if ($null -eq $line) { return '' }
    return ($line -replace "^$Name=", '').Trim()
}

function Get-DerniereSauvegarde {
    $dossier = Join-Path $Root 'backups'
    if (-not (Test-Path $dossier)) { return $null }
    return Get-ChildItem -Path $dossier -File |
        Where-Object { $_.Name -match '\.dump(\.enc)?$' } |
        Sort-Object LastWriteTime -Descending |
        Select-Object -First 1
}

function Select-TestPort {
    # Port HTTP de l'environnement de test : celui qu'il publie déjà, sinon le premier port libre
    # parmi le port souhaité puis 8001-8005, jamais celui de la production.
    param([int]$PreferredPort, [int]$ExcludedPort)
    $publie = ''
    if (Test-Path $DestEnvFile) {
        $lignes = Get-NativeLines { docker compose -f $DestComposeFile port web 8000 }
        if ($lignes -and $lignes.Count -gt 0) { $publie = ([string]$lignes[0]).Trim() -replace '^.*:', '' }
    }
    foreach ($candidat in @(@($PreferredPort) + @(8001..8005) | Select-Object -Unique)) {
        if ($candidat -eq $ExcludedPort) { continue }
        if ($publie -eq [string]$candidat) { return [int]$candidat }
        if (Test-YelenTcpPortAvailable -Port $candidat) { return [int]$candidat }
    }
    throw 'Aucun port libre entre 8001 et 8005 : préciser -Port.'
}

function Wait-ForHealth {
    # Attend que /health/ de l'environnement de test réponde « ok » avec la version attendue.
    param([int]$HttpPort, [string]$ExpectedVersion, [int]$TimeoutSeconds)
    $url = "http://127.0.0.1:$HttpPort/health/"
    $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
    while ((Get-Date) -lt $deadline) {
        try {
            $reponse = Invoke-WebRequest -Uri $url -UseBasicParsing -TimeoutSec 5
            $sante = $reponse.Content | ConvertFrom-Json
            if ($sante.status -eq 'ok' -and $sante.version -eq $ExpectedVersion) { return $true }
        } catch {
            # Service pas encore prêt (connexion refusée, 503) : nouvel essai.
        }
        Start-Sleep -Seconds 5
    }
    return $false
}

New-Item -ItemType Directory -Path $LogDirectory -Force | Out-Null
try {
    foreach ($outil in @('git', 'docker')) {
        if (-not (Get-Command $outil -ErrorAction SilentlyContinue)) { throw "$outil est introuvable dans le PATH." }
    }
    if ((Invoke-NativeQuiet { docker info }) -ne 0) { throw 'Docker ne fonctionne pas (démarrer Docker Desktop).' }
    if (-not (Test-Path $EnvFile)) { throw '.env de la production introuvable. Exécutez demarrage.bat une première fois.' }
    if ((Get-GitOutput @('-C', $Root, 'rev-parse', '--is-inside-work-tree')) -ne 'true') {
        throw "$Root n'est pas un clone git (voir le guide de déploiement, §8)."
    }
    if ($Destination -eq $Root) { throw 'La destination doit être un autre dossier que la production.' }
    foreach ($script in @($PortSelectorScript, $HostIdScript)) {
        if (-not (Test-Path $script)) { throw "Script introuvable : $script" }
    }

    $commitProduction = Get-GitOutput @('-C', $Root, 'rev-parse', 'HEAD')
    $versionProduction = (Get-Content (Join-Path $Root 'VERSION') -Raw).Trim()
    Write-Log "Production : $Root — version $versionProduction ($($commitProduction.Substring(0, 7)))."
    Write-Log "Environnement de test : $Destination."

    # ── 1. Code : même version que la production ─────────────────────────────
    $premiereCreation = -not (Test-Path (Join-Path $Destination '.git'))
    if ($premiereCreation) {
        if ((Test-Path $Destination) -and @(Get-ChildItem -Path $Destination -Force).Count -gt 0) {
            throw "$Destination existe déjà et n'est pas un environnement de test (dossier non vide sans .git)."
        }
        if ($SansRestauration) {
            throw 'Première création : la copie d''une sauvegarde est indispensable (comptes, établissement). Relancer sans -SansRestauration.'
        }
        Write-Log 'Copie du code (clone git local)...'
        if ((Invoke-Native { git clone --quiet $Root $Destination }) -ne 0) { throw 'Le clone git a échoué.' }
    } else {
        Write-Log 'Remise à niveau du code de l''environnement de test...'
        if ((Invoke-Native { git -C $Destination fetch --quiet $Root HEAD }) -ne 0) { throw 'git fetch a échoué.' }
        if ((Invoke-Native { git -C $Destination reset --hard --quiet FETCH_HEAD }) -ne 0) { throw 'git reset a échoué.' }
    }
    if ((Get-GitOutput @('-C', $Destination, 'rev-parse', 'HEAD')) -ne $commitProduction) {
        throw 'L''environnement de test n''est pas à la version de la production.'
    }
    # Même dépôt d'origine que la production : mettre-a-jour.bat lancé dans l'environnement de test
    # y installe la version publiée sur GitHub avant la production.
    $origineProduction = Get-GitOutput @('-C', $Root, 'remote', 'get-url', 'origin')
    if ($origineProduction) {
        if ((Get-GitOutput @('-C', $Destination, 'remote', 'get-url', 'origin'))) {
            [void](Invoke-NativeQuiet { git -C $Destination remote set-url origin $origineProduction })
        } else {
            [void](Invoke-NativeQuiet { git -C $Destination remote add origin $origineProduction })
        }
    }
    $versionTest = (Get-Content (Join-Path $Destination 'VERSION') -Raw).Trim()

    # ── 2. Sauvegarde à copier ──────────────────────────────────────────────
    $fichierSauvegarde = $null
    if (-not $SansRestauration) {
        if ([string]::IsNullOrWhiteSpace($Sauvegarde)) {
            $fichierSauvegarde = Get-DerniereSauvegarde
            if ($null -eq $fichierSauvegarde) {
                throw 'Aucune sauvegarde dans backups\ : lancer installer\backup-windows.bat, puis relancer.'
            }
        } else {
            if (-not [System.IO.Path]::IsPathRooted($Sauvegarde)) { $Sauvegarde = Join-Path $Root $Sauvegarde }
            if (-not (Test-Path $Sauvegarde)) { throw "Sauvegarde introuvable : $Sauvegarde" }
            $fichierSauvegarde = Get-Item $Sauvegarde
        }
        Write-Log "Sauvegarde copiée : $($fichierSauvegarde.Name) ($($fichierSauvegarde.LastWriteTime.ToString('dd/MM/yyyy HH:mm')))."
    }

    # ── 3. Port HTTP (127.0.0.1 uniquement, distinct de la production) ──────
    . $PortSelectorScript
    $portProduction = Get-DotEnvValue -Path $EnvFile -Name 'YELEN_HTTP_PORT'
    if ([string]::IsNullOrWhiteSpace($portProduction)) { $portProduction = '8000' }
    $portRetenu = Select-TestPort -PreferredPort $Port -ExcludedPort ([int]$portProduction)
    if ($portRetenu -ne $Port) { Write-Log "Le port TCP $Port est occupé ou réservé à la production : port $portRetenu retenu." }

    # ── 4. .env dérivé de la production ──────────────────────────────────────
    $clePublique = ''
    if (Test-Path $FichierCles) { $clePublique = Get-CleDepuisFichier -Path $FichierCles -Name 'LICENCE_PUBLIC_KEY' }
    $contenu = [System.IO.File]::ReadAllText($EnvFile, [System.Text.UTF8Encoding]::new($false))
    $valeurs = [ordered]@{
        'YELEN_ENVIRONNEMENT'        = 'test'
        'YELEN_HTTP_PORT'            = [string]$portRetenu
        'YELEN_WEB_BIND'             = '127.0.0.1'
        'YELEN_HTTPS'                = 'false'
        'COMPOSE_PROFILES'           = ''
        'YELEN_IMAGE'                = 'yelen-school:test'
        'ALLOWED_HOSTS'              = 'localhost,127.0.0.1'
        'CSRF_TRUSTED_ORIGINS'       = "http://localhost:$portRetenu,http://127.0.0.1:$portRetenu"
        'DISABLE_HTTPS_REDIRECT'     = 'true'
        'LICENSE_ENFORCEMENT'        = 'true'
        'LICENCE_BINDING_ENABLED'    = 'true'
        'LICENCE_ANTITAMPER_ENABLED' = 'false'
        'LICENCE_PUBLIC_KEY'         = $clePublique
        'LICENCE_HEARTBEAT_URL'      = ''
        'SMS_ENABLED'                = 'False'
        'SMS_HTTP_URL'               = ''
        'ALERTE_SMS_NUMEROS'         = ''
        'CINETPAY_API_KEY'           = ''
        'CINETPAY_SITE_ID'           = ''
        'EMAIL_HOST'                 = ''
        'YELEN_BACKUP_OFFSITE'       = ''
        'ENSURE_ADMIN'               = 'false'
        'INITIAL_ADMIN_PASSWORD'     = ''
    }
    foreach ($nom in $valeurs.Keys) { $contenu = Set-EnvLine -Content $contenu -Name $nom -Value $valeurs[$nom] }
    [System.IO.File]::WriteAllText($DestEnvFile, $contenu, [System.Text.UTF8Encoding]::new($false))
    Write-Log "Configuration .env de test écrite (port $portRetenu, contrôle des licences actif)."

    Set-Location $Destination
    # ── 5. Image Docker distincte ────────────────────────────────────────────
    Write-Log 'Construction de l''image yelen-school:test (plusieurs minutes la première fois)...'
    if ((Invoke-Native { docker compose -f $DestComposeFile build --progress plain }) -ne 0) {
        throw 'La construction de l''image a échoué.'
    }

    # ── 6. Clés de l'éditeur (une seule fois) ────────────────────────────────
    if ([string]::IsNullOrWhiteSpace($clePublique)) {
        if (Test-Path $FichierCles) { throw "Le fichier $FichierCles ne contient pas de ligne LICENCE_PUBLIC_KEY=… valide." }
        Write-Log 'Création de la paire de clés de l''éditeur (Ed25519)...'
        $lignes = Get-NativeLines { docker compose -f $DestComposeFile run --rm --no-deps -T --entrypoint python web manage.py generate_licence_keys --format env }
        if ($null -eq $lignes) { throw 'generate_licence_keys a échoué.' }
        $clePrivee = ''
        foreach ($ligne in $lignes) {
            if ($ligne -match '^LICENCE_PRIVATE_KEY=([0-9A-Fa-f]+)\s*$') { $clePrivee = $Matches[1] }
            elseif ($ligne -match '^LICENCE_PUBLIC_KEY=([0-9A-Fa-f]+)\s*$') { $clePublique = $Matches[1] }
        }
        if (-not $clePrivee -or -not $clePublique) { throw 'Clés illisibles dans la sortie de generate_licence_keys.' }
        New-Item -ItemType Directory -Path (Split-Path $FichierCles -Parent) -Force | Out-Null
        $texte = @(
            "# Clés de l'éditeur YELEN SCHOOL (Ed25519) créées le $(Get-Date -Format 'yyyy-MM-dd HH:mm').",
            '# LICENCE_PRIVATE_KEY : signe les codes de licence (installer\outils-editeur\emettre-licence.ps1).',
            '#   À conserver hors des serveurs clients (gestionnaire de mots de passe, clé USB). Jamais dans un .env.',
            '# LICENCE_PUBLIC_KEY : à copier dans le .env de chaque installation (LICENCE_PUBLIC_KEY=...).',
            "LICENCE_PRIVATE_KEY=$clePrivee",
            "LICENCE_PUBLIC_KEY=$clePublique"
        ) -join "`r`n"
        [System.IO.File]::WriteAllText($FichierCles, $texte + "`r`n", [System.Text.UTF8Encoding]::new($false))
        $contenu = Set-EnvLine -Content $contenu -Name 'LICENCE_PUBLIC_KEY' -Value $clePublique
        [System.IO.File]::WriteAllText($DestEnvFile, $contenu, [System.Text.UTF8Encoding]::new($false))
        Write-Log "Clés de l'éditeur enregistrées : $FichierCles (à mettre à l'abri)."
    } else {
        Write-Log "Clé publique de l'éditeur reprise de $FichierCles."
    }

    # ── 7. Démarrage et copie des données ────────────────────────────────────
    . $HostIdScript
    $env:YELEN_HOST_ID = Get-YelenHostId
    if ($SansRestauration) {
        Write-Log 'Démarrage des services de test...'
        if ((Invoke-Native { docker compose -f $DestComposeFile up -d }) -ne 0) { throw 'Le démarrage Docker Compose a échoué.' }
    } else {
        Write-Log 'Démarrage de la base et du cache de test...'
        if ((Invoke-Native { docker compose -f $DestComposeFile up -d --wait db redis }) -ne 0) {
            throw 'Le démarrage de la base de test a échoué.'
        }
        Write-Log 'Copie de la sauvegarde dans l''environnement de test (base + médias)...'
        $restoreScript = Join-Path $Destination 'installer\restore-windows.ps1'
        & powershell.exe -NoProfile -ExecutionPolicy Bypass -File $restoreScript $fichierSauvegarde.FullName -Yes
        if ($LASTEXITCODE -ne 0) { throw 'La copie de la sauvegarde a échoué.' }
    }

    if (-not (Wait-ForHealth -HttpPort $portRetenu -ExpectedVersion $versionTest -TimeoutSeconds $DelaiAttente)) {
        [void](Invoke-Native { docker compose -f $DestComposeFile logs --tail 30 web })
        throw 'L''environnement de test ne répond pas correctement (/health/).'
    }

    $url = "http://127.0.0.1:$portRetenu/accounts/login/"
    Write-Log "Environnement de test prêt : $url (version $versionTest, bandeau « ENVIRONNEMENT DE TEST »)."
    Write-Log 'Étape suivante : connexion Super Admin -> page « Activer la licence » -> relever Identifiant établissement et Identifiant du serveur, puis installer\outils-editeur\emettre-licence.ps1 (guide de déploiement §3.5.7).'
    if ($OuvrirNavigateur) { Start-Process $url }
} catch {
    Write-Log "ERREUR : $($_.Exception.Message)"
    exit 1
}
