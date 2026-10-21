#requires -Version 5.1
<##
.SYNOPSIS
    Déchiffre une sauvegarde YELEN SCHOOL (.dump.enc ou _media.tar.gz.enc) sans Docker.

.EXAMPLE
    .\installer\dechiffrer-sauvegarde.ps1 C:\YELEN-SAUVEGARDES\yelen_school_20261101_220000.dump.enc
    Produit yelen_school_20261101_220000.dump à côté. Phrase secrète : .env (YELEN_BACKUP_PASSPHRASE),
    -Passphrase, ou demandée à l'écran.
#>
[CmdletBinding()]
param(
    [Parameter(Mandatory = $true, Position = 0)]
    [string]$Fichier,
    [string]$Passphrase = '',
    [string]$Destination = ''
)

$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot 'yelen-crypto.ps1')
$EnvFile = Join-Path (Join-Path $PSScriptRoot '..') '.env'

if (-not (Test-Path $Fichier)) { throw "Fichier introuvable : $Fichier" }
if ($Fichier -notmatch '\.enc$') { throw 'Le fichier ne porte pas le suffixe .enc : il n''est pas chiffré.' }
if (-not $Passphrase -and (Test-Path $EnvFile)) {
    $line = Get-Content $EnvFile | Where-Object { $_ -match '^YELEN_BACKUP_PASSPHRASE=' } | Select-Object -First 1
    if ($line) { $Passphrase = ($line -replace '^YELEN_BACKUP_PASSPHRASE=', '').Trim() }
}
if (-not $Passphrase) {
    $secure = Read-Host 'Phrase secrète de sauvegarde' -AsSecureString
    $Passphrase = [Runtime.InteropServices.Marshal]::PtrToStringUni([Runtime.InteropServices.Marshal]::SecureStringToGlobalAllocUnicode($secure))
}
if (-not $Destination) { $Destination = $Fichier -replace '\.enc$', '' }

$magic = if ($Fichier -match '\.dump\.enc$') { [Text.Encoding]::ASCII.GetBytes('PGDMP') } else { [byte[]](0x1f, 0x8b) }
if (-not (Test-YelenEncryptedFile $Fichier $Passphrase $magic)) {
    throw 'Phrase secrète incorrecte ou fichier altéré.'
}

$source = [System.IO.File]::OpenRead($Fichier)
$target = [System.IO.File]::Open($Destination, [System.IO.FileMode]::Create, [System.IO.FileAccess]::Write)
try {
    $clear = Open-YelenDecryptStream $source $Passphrase
    $clear.CopyTo($target)
    $clear.Dispose()
} finally {
    $target.Dispose()
    $source.Dispose()
}
Write-Host "[OK] Fichier déchiffré : $Destination" -ForegroundColor Green
