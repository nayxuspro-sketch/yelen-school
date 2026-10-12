#requires -Version 5.1
<##
.SYNOPSIS
    Restaure une sauvegarde PostgreSQL et médias locale de YELEN SCHOOL.

.EXAMPLE
    .\installer\restore-windows.ps1 .\backups\yelen_school_20260914_220000.dump
#>

[CmdletBinding()]
param(
    [Parameter(Mandatory = $true, Position = 0)]
    [string]$BackupFile,
    [switch]$Yes
)

$ErrorActionPreference = 'Stop'
$Root = [System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))
$ComposeFile = Join-Path $Root 'docker-compose.client.yml'
$EnvFile = Join-Path $Root '.env'
if (-not [System.IO.Path]::IsPathRooted($BackupFile)) {
    $BackupFile = Join-Path $Root $BackupFile
}

function Fail {
    param([string]$Message)
    throw $Message
}

function Get-DotEnvValue {
    param([string]$Name)
    $line = Get-Content $EnvFile | Where-Object { $_ -match "^$([regex]::Escape($Name))=" } | Select-Object -First 1
    if ($null -eq $line) { return '' }
    return ($line -replace "^$([regex]::Escape($Name))=", '').Trim()
}

function Invoke-DockerRestoreFromFile {
    param(
        [string]$Arguments,
        [string]$InputFile
    )

    $psi = New-Object System.Diagnostics.ProcessStartInfo
    $psi.FileName = 'docker'
    $psi.Arguments = $Arguments
    $psi.UseShellExecute = $false
    $psi.RedirectStandardInput = $true
    $psi.RedirectStandardError = $true
    $process = New-Object System.Diagnostics.Process
    $process.StartInfo = $psi

    try {
        if (-not $process.Start()) { Fail 'Impossible de démarrer Docker pour la restauration.' }
        # Lire stderr en parallèle évite un blocage pendant l'envoi du dump.
        $errorTask = $process.StandardError.ReadToEndAsync()
        $inputStream = [System.IO.File]::OpenRead($InputFile)
        try {
            $inputStream.CopyTo($process.StandardInput.BaseStream)
        } catch [System.IO.IOException] {
            # pg_restore ferme son entrée dès qu'il a lu ce dont il a besoin, avant
            # la fin d'une archive custom : le tube est rompu alors que l'import a
            # réussi. Seul le code de sortie fait foi.
        } finally {
            $inputStream.Dispose()
            try { $process.StandardInput.Close() } catch [System.IO.IOException] { }
        }
        $process.WaitForExit()
        $errorOutput = $errorTask.Result
        if ($process.ExitCode -ne 0) {
            Fail $errorOutput
        }
    } finally {
        $process.Dispose()
    }
}

if (-not (Test-Path $BackupFile)) { Fail "Sauvegarde introuvable : $BackupFile" }
if (-not (Get-Command docker -ErrorAction SilentlyContinue)) { Fail 'Docker est introuvable.' }
& docker info *> $null
if ($LASTEXITCODE -ne 0) { Fail 'Docker ne fonctionne pas.' }
if (-not (Test-Path $ComposeFile)) { Fail "Fichier introuvable : $ComposeFile" }
if (-not (Test-Path $EnvFile)) { Fail '.env est introuvable.' }

$dbName = Get-DotEnvValue 'DB_NAME'
$dbUser = Get-DotEnvValue 'DB_USER'
if ([string]::IsNullOrWhiteSpace($dbName)) { $dbName = 'yelen_school_db' }
if ([string]::IsNullOrWhiteSpace($dbUser)) { $dbUser = 'yelen_user' }
# ChangeExtension($BackupFile, $null) laisse un point final sous PowerShell ($null devient '') : le nom est reconstruit.
$mediaFile = [System.IO.Path]::Combine([System.IO.Path]::GetDirectoryName($BackupFile), [System.IO.Path]::GetFileNameWithoutExtension($BackupFile) + '_media.tar.gz')

if (-not $Yes) {
    Write-Host 'ATTENTION : cette opération remplace toutes les données de la base et des médias.' -ForegroundColor Yellow
    $confirmation = Read-Host 'Tapez RESTAURER pour continuer'
    if ($confirmation -cne 'RESTAURER') { Fail 'Restauration annulée.' }
}

Write-Host '[1/5] Arrêt de l''application...' -ForegroundColor Cyan
& docker compose -f $ComposeFile stop web
if ($LASTEXITCODE -ne 0) { Fail 'Impossible d''arrêter le service web.' }

# Le dump est importé dans une base temporaire, puis les bases sont permutées
# par renommage : un dump illisible laisse la base actuelle intacte, et la base
# remplacée reste disponible sous <DB_NAME>_avant_restauration.
$dbRestore = "${dbName}_restauration"
$dbPrevious = "${dbName}_avant_restauration"
try {
    Write-Host '[2/5] Import de la base PostgreSQL dans une base temporaire...' -ForegroundColor Cyan
    & docker compose -f $ComposeFile exec -T db dropdb --if-exists -U $dbUser $dbRestore
    if ($LASTEXITCODE -ne 0) { Fail 'Impossible de préparer la base temporaire.' }
    & docker compose -f $ComposeFile exec -T db createdb -U $dbUser -O $dbUser $dbRestore
    if ($LASTEXITCODE -ne 0) { Fail 'Impossible de créer la base temporaire.' }

    # pg_restore lit l'entrée standard quand aucun fichier n'est indiqué ("-" n'est pas reconnu).
    $dbArguments = "compose -f `"$ComposeFile`" exec -T db pg_restore -U $dbUser -d $dbRestore --no-owner --no-privileges --exit-on-error"
    try {
        Invoke-DockerRestoreFromFile $dbArguments $BackupFile
    } catch {
        & docker compose -f $ComposeFile exec -T db dropdb --if-exists -U $dbUser $dbRestore
        throw "Import impossible, la base actuelle est inchangée : $($_.Exception.Message)"
    }

    Write-Host "[3/5] Bascule vers la base restaurée (base remplacée conservée sous $dbPrevious)..." -ForegroundColor Cyan
    & docker compose -f $ComposeFile exec -T db dropdb --if-exists -U $dbUser $dbPrevious
    if ($LASTEXITCODE -ne 0) { Fail "Impossible de supprimer la copie précédente $dbPrevious." }
    & docker compose -f $ComposeFile exec -T db psql -U $dbUser -d postgres -q -v ON_ERROR_STOP=1 -c "ALTER DATABASE $dbName RENAME TO $dbPrevious; ALTER DATABASE $dbRestore RENAME TO $dbName;"
    if ($LASTEXITCODE -ne 0) { Fail 'La bascule a échoué (une session est encore ouverte sur la base ?). La base actuelle est inchangée.' }

    & docker compose -f $ComposeFile up -d web | Out-Host
    if ($LASTEXITCODE -ne 0) { Fail 'Impossible de redémarrer le service web.' }

    if (Test-Path $mediaFile) {
        $mediaArguments = "compose -f `"$ComposeFile`" exec -T web python /app/installer/media_archive.py restore"
        Write-Host '[4/5] Import des médias...' -ForegroundColor Cyan
        Invoke-DockerRestoreFromFile $mediaArguments $mediaFile
    } else {
        Write-Host "[AVERTISSEMENT] Archive médias absente : $mediaFile" -ForegroundColor Yellow
        Write-Host 'La base est restaurée, mais les fichiers téléversés ne le sont pas.' -ForegroundColor Yellow
    }

    Write-Host '[5/5] Contrôle fonctionnel post-restauration...' -ForegroundColor Cyan
    & docker compose -f $ComposeFile exec -T web python manage.py check
    if ($LASTEXITCODE -ne 0) { Fail 'La vérification Django a échoué après la restauration.' }

    $healthCode = "import json,urllib.request; d=json.load(urllib.request.urlopen('http://127.0.0.1:8000/health/', timeout=5)); assert d.get('status') == 'ok' and d.get('database') == 'ok' and d.get('cache') == 'ok'"
    $healthOk = $false
    for ($attempt = 1; $attempt -le 30; $attempt++) {
        & docker compose -f $ComposeFile exec -T web python -c $healthCode *> $null
        if ($LASTEXITCODE -eq 0) {
            $healthOk = $true
            break
        }
        Start-Sleep -Seconds 2
    }
    if (-not $healthOk) { Fail 'Le contrôle /health/ a échoué après la restauration.' }
} finally {
    Write-Host 'Vérification du démarrage de YELEN SCHOOL...' -ForegroundColor Cyan
    & docker compose -f $ComposeFile up -d web | Out-Host
}

Write-Host '[OK] Restauration terminée et contrôle /health/ réussi.' -ForegroundColor Green
Write-Host 'Vérifiez aussi la connexion et quelques données dans l''application.'
