#requires -Version 5.1
<##
.SYNOPSIS
    Essai de restauration de YELEN SCHOOL : vérifie qu'une sauvegarde est réellement exploitable.

.DESCRIPTION
    La dernière sauvegarde (ou celle passée en -BackupFile) est importée dans une base
    temporaire <DB_NAME>_test_restauration, les tables et quelques effectifs sont contrôlés,
    puis la base temporaire est supprimée. La production n'est jamais touchée : l'application
    reste en marche et aucune donnée n'est remplacée.

    Le résultat est consigné dans backups\restauration.log et apparaît dans
    Administration > Exploitation, carte « Restauration testée ».

.EXAMPLE
    .\installer\tester-restauration.ps1

.EXAMPLE
    .\installer\tester-restauration.ps1 -BackupFile .\backups\yelen_school_20261102_020000.dump.enc

.NOTES
    À exécuter une fois par trimestre. Accepter -KeepBase conserve la base temporaire
    pour inspection (à supprimer ensuite avec dropdb).
#>

[CmdletBinding()]
param(
    [string]$BackupFile = '',
    [switch]$KeepBase
)

$ErrorActionPreference = 'Stop'
$Root = [System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))
$ComposeFile = Join-Path $Root 'docker-compose.client.yml'
$EnvFile = Join-Path $Root '.env'
$BackupDirectory = Join-Path $Root 'backups'
$LogFile = Join-Path $BackupDirectory 'restauration.log'
. (Join-Path $PSScriptRoot 'yelen-crypto.ps1')

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

function Write-Resultat {
    param([string]$Resultat, [string]$Detail)
    New-Item -ItemType Directory -Path $BackupDirectory -Force | Out-Null
    $ligne = '{0} {1} {2}' -f (Get-Date -Format 'yyyy-MM-dd HH:mm:ss'), $Resultat, $Detail
    Add-Content -Path $LogFile -Value $ligne -Encoding UTF8
    Write-Host "Consigné dans $LogFile" -ForegroundColor DarkGray
}

function Invoke-DockerRestoreFromFile {
    param(
        [string]$Arguments,
        [string]$InputFile,
        [string]$Passphrase = ''
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
        if (-not $process.Start()) { Fail 'Impossible de démarrer Docker pour l''essai de restauration.' }
        $errorTask = $process.StandardError.ReadToEndAsync()
        $fileStream = [System.IO.File]::OpenRead($InputFile)
        $inputStream = $fileStream
        try {
            if ($Passphrase) { $inputStream = Open-YelenDecryptStream $fileStream $Passphrase }
            $inputStream.CopyTo($process.StandardInput.BaseStream)
        } catch [System.IO.IOException] {
            # pg_restore ferme son entrée dès qu'il a lu ce dont il a besoin : seul le code de sortie fait foi.
        } finally {
            try { $inputStream.Dispose() } catch [System.Security.Cryptography.CryptographicException] { }
            $fileStream.Dispose()
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

if (-not (Get-Command docker -ErrorAction SilentlyContinue)) { Fail 'Docker est introuvable.' }
& docker info *> $null
if ($LASTEXITCODE -ne 0) { Fail 'Docker ne fonctionne pas.' }
if (-not (Test-Path $ComposeFile)) { Fail "Fichier introuvable : $ComposeFile" }
if (-not (Test-Path $EnvFile)) { Fail '.env est introuvable.' }

$dbName = Get-DotEnvValue 'DB_NAME'
$dbUser = Get-DotEnvValue 'DB_USER'
if ([string]::IsNullOrWhiteSpace($dbName)) { $dbName = 'yelen_school_db' }
if ([string]::IsNullOrWhiteSpace($dbUser)) { $dbUser = 'yelen_user' }
$passphrase = Get-DotEnvValue 'YELEN_BACKUP_PASSPHRASE'

if (-not $BackupFile) {
    if (-not (Test-Path $BackupDirectory)) { Fail "Aucun dossier de sauvegarde : $BackupDirectory" }
    $dernier = Get-ChildItem -Path $BackupDirectory -Filter 'yelen_school_*.dump*' -File |
        Where-Object { $_.Name -match '\.dump(\.enc)?$' } |
        Sort-Object LastWriteTime -Descending |
        Select-Object -First 1
    if ($null -eq $dernier) { Fail "Aucune sauvegarde dans $BackupDirectory : lancer backup-windows.bat." }
    $BackupFile = $dernier.FullName
} elseif (-not [System.IO.Path]::IsPathRooted($BackupFile)) {
    $BackupFile = Join-Path $Root $BackupFile
}
if (-not (Test-Path $BackupFile)) { Fail "Sauvegarde introuvable : $BackupFile" }

$nomFichier = [System.IO.Path]::GetFileName($BackupFile)
$encrypted = $BackupFile -match '\.enc$'
if ($encrypted) {
    if (-not $passphrase) { Fail 'Sauvegarde chiffrée : renseignez YELEN_BACKUP_PASSPHRASE dans .env.' }
    if (-not (Test-YelenEncryptedFile $BackupFile $passphrase ([Text.Encoding]::ASCII.GetBytes('PGDMP')))) {
        $detail = "fichier=$nomFichier motif=phrase-secrete-incorrecte-ou-fichier-altere"
        Write-Resultat 'ECHEC' $detail
        Fail 'Phrase secrète incorrecte ou fichier altéré : la sauvegarde est inexploitable.'
    }
} else {
    $passphrase = ''
}

$dbTest = "${dbName}_test_restauration"
$debut = Get-Date
Write-Host "Essai de restauration de $nomFichier dans $dbTest (la production n'est pas touchée)." -ForegroundColor Cyan

try {
    & docker compose -f $ComposeFile exec -T db dropdb --if-exists -U $dbUser $dbTest
    if ($LASTEXITCODE -ne 0) { Fail 'Impossible de préparer la base de test.' }
    & docker compose -f $ComposeFile exec -T db createdb -U $dbUser -O $dbUser $dbTest
    if ($LASTEXITCODE -ne 0) { Fail 'Impossible de créer la base de test.' }

    $dbArguments = "compose -f `"$ComposeFile`" exec -T db pg_restore -U $dbUser -d $dbTest --no-owner --no-privileges --exit-on-error"
    Invoke-DockerRestoreFromFile $dbArguments $BackupFile $passphrase

    # Contrôle : tables présentes et effectifs lisibles.
    $sql = 'SELECT (SELECT count(*) FROM information_schema.tables WHERE table_schema = ''public''), ' +
           '(SELECT count(*) FROM inscriptions_eleve), (SELECT count(*) FROM inscriptions_inscription), ' +
           '(SELECT count(*) FROM finances_paiement);'
    $mesures = (& docker compose -f $ComposeFile exec -T db psql -U $dbUser -d $dbTest -t -A -F ' ' -c $sql | Out-String).Trim()
    if ($LASTEXITCODE -ne 0 -or -not $mesures) { Fail 'Les tables restaurées ne sont pas lisibles.' }
    $valeurs = $mesures -split '\s+'
    if ($valeurs.Count -lt 4) { Fail "Réponse inattendue du contrôle : $mesures" }
    $tables = [int]$valeurs[0]; $eleves = [int]$valeurs[1]; $inscriptions = [int]$valeurs[2]; $paiements = [int]$valeurs[3]
    if ($tables -lt 30) { Fail "Seulement $tables table(s) restaurée(s) : la sauvegarde est incomplète." }
    if ($eleves -lt 1) { Fail 'Aucun élève restauré : la sauvegarde ne contient pas les données attendues.' }

    $duree = [int]((Get-Date) - $debut).TotalSeconds
    $detail = "fichier=$nomFichier tables=$tables eleves=$eleves inscriptions=$inscriptions paiements=$paiements duree=${duree}s"
    Write-Resultat 'OK' $detail
    Write-Host "[OK] Restauration vérifiée en ${duree} s : $tables tables, $eleves élèves, $paiements paiements." -ForegroundColor Green
} catch {
    $motif = ($_.Exception.Message -replace '\s+', ' ')
    if ($motif.Length -gt 160) { $motif = $motif.Substring(0, 160) }
    Write-Resultat 'ECHEC' "fichier=$nomFichier motif=$motif"
    Write-Host "[ECHEC] $motif" -ForegroundColor Red
    throw
} finally {
    if ($KeepBase) {
        Write-Host "Base de test conservée : $dbTest (supprimer avec : docker compose -f docker-compose.client.yml exec -T db dropdb -U $dbUser $dbTest)" -ForegroundColor Yellow
    } else {
        & docker compose -f $ComposeFile exec -T db dropdb --if-exists -U $dbUser $dbTest *> $null
    }
}
