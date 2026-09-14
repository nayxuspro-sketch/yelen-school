#requires -Version 5.1
<##
.SYNOPSIS
    Sauvegarde la base PostgreSQL locale de YELEN SCHOOL.
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
$temporaryFile = "$backupFile.part"

$arguments = "compose -f `"$ComposeFile`" exec -T db pg_dump -U $dbUser -d $dbName --format=custom"
$psi = New-Object System.Diagnostics.ProcessStartInfo
$psi.FileName = 'docker'
$psi.Arguments = $arguments
$psi.UseShellExecute = $false
$psi.RedirectStandardOutput = $true
$psi.RedirectStandardError = $true
$process = New-Object System.Diagnostics.Process
$process.StartInfo = $psi

try {
    Write-Host "[1/2] Export de PostgreSQL vers $backupFile"
    if (-not $process.Start()) { Fail 'Impossible de démarrer Docker.' }

    $outputStream = [System.IO.File]::Open($temporaryFile, [System.IO.FileMode]::Create, [System.IO.FileAccess]::Write)
    try {
        $process.StandardOutput.BaseStream.CopyTo($outputStream)
    } finally {
        $outputStream.Dispose()
    }

    $errorOutput = $process.StandardError.ReadToEnd()
    $process.WaitForExit()
    if ($process.ExitCode -ne 0) {
        Fail "La sauvegarde PostgreSQL a échoué : $errorOutput"
    }

    if (-not (Test-Path $temporaryFile) -or (Get-Item $temporaryFile).Length -eq 0) {
        Fail 'Le fichier de sauvegarde est vide.'
    }
    Move-Item -Force $temporaryFile $backupFile
} finally {
    if (Test-Path $temporaryFile) { Remove-Item -Force $temporaryFile }
    $process.Dispose()
}

Get-ChildItem -Path $OutputDirectory -Filter 'yelen_school_*.dump' -File |
    Sort-Object LastWriteTime -Descending |
    Select-Object -Skip $Keep |
    Remove-Item -Force

Write-Host "[2/2] Sauvegarde terminée : $backupFile"
Write-Host "Rétention appliquée : $Keep sauvegarde(s) maximum"
