#requires -Version 5.1
<##
.SYNOPSIS
    Restaure une sauvegarde PostgreSQL locale de YELEN SCHOOL.

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

if (-not $Yes) {
    Write-Host 'ATTENTION : cette opération remplace toutes les données de la base.' -ForegroundColor Yellow
    $confirmation = Read-Host 'Tapez RESTAURER pour continuer'
    if ($confirmation -cne 'RESTAURER') { Fail 'Restauration annulée.' }
}

Write-Host '[1/3] Arrêt de l’application...' -ForegroundColor Cyan
& docker compose -f $ComposeFile stop web
if ($LASTEXITCODE -ne 0) { Fail 'Impossible d’arrêter le service web.' }

try {
    Write-Host '[2/3] Reconstruction de la base PostgreSQL...' -ForegroundColor Cyan
    & docker compose -f $ComposeFile exec -T db dropdb --if-exists -U $dbUser $dbName
    if ($LASTEXITCODE -ne 0) { Fail 'Impossible de supprimer la base actuelle.' }
    & docker compose -f $ComposeFile exec -T db createdb -U $dbUser -O $dbUser $dbName
    if ($LASTEXITCODE -ne 0) { Fail 'Impossible de créer la base restaurée.' }

    $arguments = "compose -f `"$ComposeFile`" exec -T db pg_restore -U $dbUser -d $dbName --no-owner --no-privileges --exit-on-error -"
    $psi = New-Object System.Diagnostics.ProcessStartInfo
    $psi.FileName = 'docker'
    $psi.Arguments = $arguments
    $psi.UseShellExecute = $false
    $psi.RedirectStandardInput = $true
    $psi.RedirectStandardError = $true
    $process = New-Object System.Diagnostics.Process
    $process.StartInfo = $psi

    try {
        Write-Host '[3/3] Import de la sauvegarde...' -ForegroundColor Cyan
        if (-not $process.Start()) { Fail 'Impossible de démarrer Docker pour la restauration.' }
        $inputStream = [System.IO.File]::OpenRead($BackupFile)
        try {
            $inputStream.CopyTo($process.StandardInput.BaseStream)
        } finally {
            $inputStream.Dispose()
            $process.StandardInput.Close()
        }
        $errorOutput = $process.StandardError.ReadToEnd()
        $process.WaitForExit()
        if ($process.ExitCode -ne 0) {
            Fail "La restauration PostgreSQL a échoué : $errorOutput"
        }
    } finally {
        $process.Dispose()
    }
} finally {
    Write-Host 'Redémarrage de YELEN SCHOOL...' -ForegroundColor Cyan
    & docker compose -f $ComposeFile up -d web | Out-Host
}

Write-Host '[OK] Restauration terminée. Vérifiez quelques données dans l’application.' -ForegroundColor Green
