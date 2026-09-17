#requires -Version 5.1
<##
.SYNOPSIS
    Sauvegarde la base PostgreSQL et les médias locaux de YELEN SCHOOL.
#>

[CmdletBinding()]
param(
    [string]$OutputDirectory = '',
    [ValidateRange(1, 3650)]
    [int]$Keep = 30
)

$ErrorActionPreference = 'Stop'
$Root = [System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))
$ComposeFile = Join-Path $Root 'docker-compose.client.yml'
$EnvFile = Join-Path $Root '.env'
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

function Invoke-DockerStreamToFile {
    param(
        [string]$Arguments,
        [string]$OutputFile
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
        $outputStream = [System.IO.File]::Open($OutputFile, [System.IO.FileMode]::Create, [System.IO.FileAccess]::Write)
        try {
            $process.StandardOutput.BaseStream.CopyTo($outputStream)
        } finally {
            $outputStream.Dispose()
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
if (-not (Test-Path $EnvFile)) { Fail '.env est introuvable. Lancez d’abord l’installation locale.' }

$dbName = Get-DotEnvValue 'DB_NAME'
$dbUser = Get-DotEnvValue 'DB_USER'
if ([string]::IsNullOrWhiteSpace($dbName)) { $dbName = 'yelen_school_db' }
if ([string]::IsNullOrWhiteSpace($dbUser)) { $dbUser = 'yelen_user' }

New-Item -ItemType Directory -Path $OutputDirectory -Force | Out-Null
$timestamp = Get-Date -Format 'yyyyMMdd_HHmmss'
$backupFile = Join-Path $OutputDirectory "yelen_school_$timestamp.dump"
$mediaFile = Join-Path $OutputDirectory "yelen_school_${timestamp}_media.tar.gz"
$dbTemporaryFile = "$backupFile.part"
$mediaTemporaryFile = "$mediaFile.part"

try {
    Write-Host "[1/3] Export de PostgreSQL vers $backupFile"
    $dbArguments = "compose -f `"$ComposeFile`" exec -T db pg_dump -U $dbUser -d $dbName --format=custom"
    Invoke-DockerStreamToFile $dbArguments $dbTemporaryFile
    if (-not (Test-Path $dbTemporaryFile) -or (Get-Item $dbTemporaryFile).Length -eq 0) {
        Fail 'Le fichier de sauvegarde PostgreSQL est vide.'
    }
    Move-Item -Force $dbTemporaryFile $backupFile

    Write-Host "[2/3] Export des médias vers $mediaFile"
    $mediaArguments = "compose -f `"$ComposeFile`" exec -T web python /app/installer/media_archive.py create"
    try {
        Invoke-DockerStreamToFile $mediaArguments $mediaTemporaryFile
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

Get-ChildItem -Path $OutputDirectory -Filter 'yelen_school_*.dump' -File |
    Sort-Object LastWriteTime -Descending |
    Select-Object -Skip $Keep |
    ForEach-Object {
        Remove-Item -Force $_.FullName
        $oldMedia = [System.IO.Path]::ChangeExtension($_.FullName, $null) + '_media.tar.gz'
        if (Test-Path $oldMedia) { Remove-Item -Force $oldMedia }
    }

Write-Host '[3/3] Sauvegarde terminée'
Write-Host "  Base PostgreSQL : $backupFile"
Write-Host "  Médias          : $mediaFile"
Write-Host "  Rétention       : $Keep sauvegarde(s) maximum"
