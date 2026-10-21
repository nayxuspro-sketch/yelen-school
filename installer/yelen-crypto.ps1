#requires -Version 5.1
<##
.SYNOPSIS
    Chiffrement AES-256 des sauvegardes YELEN SCHOOL (fonctions partagées, à inclure avec « . »).

.DESCRIPTION
    Format identique à « openssl enc -aes-256-cbc -pbkdf2 -iter 200000 -md sha256 -salt » :
    en-tête « Salted__ » + sel de 8 octets, clé et IV dérivés par PBKDF2-HMAC-SHA256.
    Un fichier .enc se déchiffre donc aussi sans YELEN SCHOOL, sur n'importe quelle machine :
      openssl enc -d -aes-256-cbc -pbkdf2 -iter 200000 -md sha256 -in fichier.enc -out fichier
    Les scripts ne placent jamais la phrase secrète sur une ligne de commande.
#>

$script:YelenCryptoIterations = 200000
$script:YelenCryptoHeader = [Text.Encoding]::ASCII.GetBytes('Salted__')

function New-YelenAes {
    param([string]$Passphrase, [byte[]]$Salt)
    $derivation = New-Object System.Security.Cryptography.Rfc2898DeriveBytes(
        [Text.Encoding]::UTF8.GetBytes($Passphrase), $Salt, $script:YelenCryptoIterations,
        [System.Security.Cryptography.HashAlgorithmName]::SHA256)
    try {
        $bytes = $derivation.GetBytes(48)
    } finally {
        $derivation.Dispose()
    }
    $aes = [System.Security.Cryptography.Aes]::Create()
    $aes.KeySize = 256
    $aes.Mode = [System.Security.Cryptography.CipherMode]::CBC
    $aes.Padding = [System.Security.Cryptography.PaddingMode]::PKCS7
    $aes.Key = $bytes[0..31]
    $aes.IV = $bytes[32..47]
    return $aes
}

function New-YelenEncryptStream {
    <# Écrit l'en-tête dans $Target et renvoie le flux à alimenter en clair (à fermer pour finaliser). #>
    param([System.IO.Stream]$Target, [string]$Passphrase)
    $salt = New-Object byte[] 8
    $rng = [System.Security.Cryptography.RandomNumberGenerator]::Create()
    try { $rng.GetBytes($salt) } finally { $rng.Dispose() }
    $Target.Write($script:YelenCryptoHeader, 0, 8)
    $Target.Write($salt, 0, 8)
    $aes = New-YelenAes $Passphrase $salt
    return New-Object System.Security.Cryptography.CryptoStream(
        $Target, $aes.CreateEncryptor(), [System.Security.Cryptography.CryptoStreamMode]::Write)
}

function Open-YelenDecryptStream {
    <# Lit l'en-tête de $Source et renvoie le flux déchiffré en lecture. #>
    param([System.IO.Stream]$Source, [string]$Passphrase)
    $header = New-Object byte[] 16
    $read = 0
    while ($read -lt 16) {
        $n = $Source.Read($header, $read, 16 - $read)
        if ($n -le 0) { break }
        $read += $n
    }
    if ($read -lt 16 -or [Text.Encoding]::ASCII.GetString($header, 0, 8) -ne 'Salted__') {
        throw 'Ce fichier n''est pas une sauvegarde chiffrée YELEN SCHOOL (en-tête absent).'
    }
    $aes = New-YelenAes $Passphrase $header[8..15]
    return New-Object System.Security.Cryptography.CryptoStream(
        $Source, $aes.CreateDecryptor(), [System.Security.Cryptography.CryptoStreamMode]::Read)
}

function Test-YelenEncryptedFile {
    <# Vérifie la phrase secrète sans tout déchiffrer : les premiers octets doivent correspondre à $Magic. #>
    param([string]$Path, [string]$Passphrase, [byte[]]$Magic)
    $file = [System.IO.File]::OpenRead($Path)
    try {
        $clear = Open-YelenDecryptStream $file $Passphrase
        $buffer = New-Object byte[] $Magic.Length
        $read = 0
        while ($read -lt $buffer.Length) {
            $n = $clear.Read($buffer, $read, $buffer.Length - $read)
            if ($n -le 0) { break }
            $read += $n
        }
        if ($read -ne $Magic.Length) { return $false }
        for ($i = 0; $i -lt $Magic.Length; $i++) {
            if ($buffer[$i] -ne $Magic[$i]) { return $false }
        }
        return $true
    } catch [System.Security.Cryptography.CryptographicException] {
        return $false
    } finally {
        $file.Dispose()
    }
}
