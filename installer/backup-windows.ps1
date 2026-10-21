#requires -Version 5.1
<##
.SYNOPSIS
    Sauvegarde la base PostgreSQL et les médias locaux de YELEN SCHOOL.

.DESCRIPTION
    Si YELEN_BACKUP_PASSPHRASE est renseignée dans .env, les deux fichiers sont
    chiffrés AES-256 (suffixe .enc, format compatible openssl). Si
    YELEN_BACKUP_OFFSITE désigne un dossier (disque externe, NAS), la paire y est
    copiée avec la même rétention.
#>

[CmdletBinding()]
param(
    [string]$OutputDirectory = '',
    [ValidateRange(1, 3650)]
    [int]$Keep = 30,
    [string]$OffsiteDirectory = ''
)

$ErrorActionPreference = 'Stop'
$Root = [System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))
$ComposeFile = Join-Path $Root 'docker-compose.client.yml'
$EnvFile = Join-Path $Root '.env'
. (Join-Path $PSScriptRoot 'yelen-crypto.ps1')
if ([string]::IsNullOrWhiteSpace($OutputDirectory)) {
    $OutputDirectory = Join-Path $Root 'backups'
} elseif (-not [System.IO.Path]::IsPathRooted($OutputDirectory)) {
    $OutputDirectory = Join-Path $Root $OutputDirectory
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

function Remove-OldBackups {
    param([string]$Directory)
    Get-ChildItem -Path $Directory -Filter 'yelen_school_*.dump*' -File |
        Where-Object { $_.Name -match '\.dump(\.enc)?$' } |
        Sort-Object LastWriteTime -Descending |
        Select-Object -Skip $Keep |
        ForEach-Object {
            Remove-Item -Force $_.FullName
            $stem = $_.Name -replace '\.dump(\.enc)?$', ''
            foreach ($suffix in '_media.tar.gz', '_media.tar.gz.enc') {
                $oldMedia = Join-Path $_.DirectoryName ($stem + $suffix)
                if (Test-Path $oldMedia) { Remove-Item -Force $oldMedia }
            }
        }
}

function Invoke-DockerStreamToFile {
    param(
        [string]$Arguments,
        [string]$OutputFile,
        [string]$Passphrase = ''
    )

    $psi = New-Object System.Diagnostics.ProcessStartInfo
    $psi.FileName = 'docker'
    $psi.Arguments = $Arguments
    $psi.UseShellExecute = $false
    $psi.RedirectStandardOutput = $true
    $psi.RedirectStandardError = $true
    $process = New-Object System.Diagnostics.Process
    $process.StartInfo = $psi

    try {
        if (-not $process.Start()) { Fail 'Impossible de démarrer Docker.' }
        # Lire stderr en parallèle évite de bloquer si Docker remplit son
        # tampon d'erreurs pendant que le dump est encore en cours.
        $errorTask = $process.StandardError.ReadToEndAsync()
        $fileStream = [System.IO.File]::Open($OutputFile, [System.IO.FileMode]::Create, [System.IO.FileAccess]::Write)
        $outputStream = $fileStream
        try {
            if ($Passphrase) { $outputStream = New-YelenEncryptStream $fileStream $Passphrase }
            $process.StandardOutput.BaseStream.CopyTo($outputStream)
        } finally {
            $outputStream.Dispose()
            $fileStream.Dispose()
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

if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
    Fail 'Docker est introuvable.'
}
& docker info *> $null
if ($LASTEXITCODE -ne 0) { Fail 'Docker ne fonctionne pas.' }
if (-not (Test-Path $ComposeFile)) { Fail "Fichier introuvable : $ComposeFile" }
if (-not (Test-Path $EnvFile)) { Fail '.env est introuvable. Lancez d''abord l''installation locale.' }

$dbName = Get-DotEnvValue 'DB_NAME'
$dbUser = Get-DotEnvValue 'DB_USER'
if ([string]::IsNullOrWhiteSpace($dbName)) { $dbName = 'yelen_school_db' }
if ([string]::IsNullOrWhiteSpace($dbUser)) { $dbUser = 'yelen_user' }
$passphrase = Get-DotEnvValue 'YELEN_BACKUP_PASSPHRASE'
if ([string]::IsNullOrWhiteSpace($OffsiteDirectory)) { $OffsiteDirectory = Get-DotEnvValue 'YELEN_BACKUP_OFFSITE' }
$encSuffix = ''
if ($passphrase) {
    if ($passphrase.Length -lt 12) { Fail 'YELEN_BACKUP_PASSPHRASE doit contenir au moins 12 caractères.' }
    $encSuffix = '.enc'
} else {
    Write-Host '[AVERTISSEMENT] YELEN_BACKUP_PASSPHRASE absente du .env : sauvegarde EN CLAIR.' -ForegroundColor Yellow
}

New-Item -ItemType Directory -Path $OutputDirectory -Force | Out-Null
$timestamp = Get-Date -Format 'yyyyMMdd_HHmmss'
$backupFile = Join-Path $OutputDirectory "yelen_school_$timestamp.dump$encSuffix"
$mediaFile = Join-Path $OutputDirectory "yelen_school_${timestamp}_media.tar.gz$encSuffix"
$dbTemporaryFile = "$backupFile.part"
$mediaTemporaryFile = "$mediaFile.part"

try {
    Write-Host "[1/3] Export de PostgreSQL vers $backupFile"
    $dbArguments = "compose -f `"$ComposeFile`" exec -T db pg_dump -U $dbUser -d $dbName --format=custom"
    Invoke-DockerStreamToFile $dbArguments $dbTemporaryFile $passphrase
    if (-not (Test-Path $dbTemporaryFile) -or (Get-Item $dbTemporaryFile).Length -eq 0) {
        Fail 'Le fichier de sauvegarde PostgreSQL est vide.'
    }
    Move-Item -Force $dbTemporaryFile $backupFile

    Write-Host "[2/3] Export des médias vers $mediaFile"
    $mediaArguments = "compose -f `"$ComposeFile`" exec -T web python /app/installer/media_archive.py create"
    try {
        Invoke-DockerStreamToFile $mediaArguments $mediaTemporaryFile $passphrase
    } catch {
        Remove-Item -Force $backupFile -ErrorAction SilentlyContinue
        throw "La sauvegarde des médias a échoué : $($_.Exception.Message)"
    }
    if (-not (Test-Path $mediaTemporaryFile) -or (Get-Item $mediaTemporaryFile).Length -eq 0) {
        Remove-Item -Force $backupFile -ErrorAction SilentlyContinue
        Fail 'Le fichier de sauvegarde des médias est vide.'
    }
    Move-Item -Force $mediaTemporaryFile $mediaFile
} finally {
    if (Test-Path $dbTemporaryFile) { Remove-Item -Force $dbTemporaryFile }
    if (Test-Path $mediaTemporaryFile) { Remove-Item -Force $mediaTemporaryFile }
}

Remove-OldBackups $OutputDirectory

$offsiteStatus = 'non configurée (YELEN_BACKUP_OFFSITE)'
if ($OffsiteDirectory) {
    try {
        New-Item -ItemType Directory -Path $OffsiteDirectory -Force -ErrorAction Stop | Out-Null
        Copy-Item -LiteralPath $backupFile, $mediaFile -Destination $OffsiteDirectory -Force -ErrorAction Stop
        Remove-OldBackups $OffsiteDirectory
        $offsiteStatus = $OffsiteDirectory
    } catch {
        $offsiteStatus = "ÉCHEC vers $OffsiteDirectory ($($_.Exception.Message))"
        Write-Host "[AVERTISSEMENT] Copie hors site impossible : $($_.Exception.Message)" -ForegroundColor Yellow
    }
}

Write-Host '[3/3] Sauvegarde terminée'
Write-Host "  Base PostgreSQL : $backupFile"
Write-Host "  Médias          : $mediaFile"
Write-Host "  Chiffrement     : $(if ($passphrase) { 'AES-256 (YELEN_BACKUP_PASSPHRASE)' } else { 'AUCUN' })"
Write-Host "  Copie hors site : $offsiteStatus"
Write-Host "  Rétention       : $Keep sauvegarde(s) maximum"
