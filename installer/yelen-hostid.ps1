#requires -Version 5.1
<##
.SYNOPSIS
    Identifiant stable de ce serveur (YELEN_HOST_ID) pour la liaison des licences.

.DESCRIPTION
    SHA-256 des attributs matériels et système de la machine : MachineGuid
    Windows, UUID SMBIOS, numéro de série de la carte mère et du disque
    système. L'identifiant est recalculé à chaque démarrage et transmis au
    conteneur web (variable YELEN_HOST_ID) : il n'est jamais écrit dans un
    fichier. Une copie du dossier sur une autre machine produit un autre
    identifiant, donc une licence refusée.

    Exécuté directement : affiche l'identifiant (à transmettre à l'éditeur).
    Dot-sourcé (. .\yelen-hostid.ps1) : expose la fonction Get-YelenHostId.
#>

function Get-YelenHostId {
    $attributs = New-Object System.Collections.Generic.List[string]

    try {
        $attributs.Add([string](Get-ItemProperty -Path 'HKLM:\SOFTWARE\Microsoft\Cryptography' -Name MachineGuid -ErrorAction Stop).MachineGuid)
    } catch { $attributs.Add('') }

    try {
        $attributs.Add([string](Get-CimInstance -ClassName Win32_ComputerSystemProduct -ErrorAction Stop).UUID)
    } catch { $attributs.Add('') }

    try {
        $attributs.Add([string](Get-CimInstance -ClassName Win32_BaseBoard -ErrorAction Stop).SerialNumber)
    } catch { $attributs.Add('') }

    try {
        $lettre = $env:SystemDrive.TrimEnd(':')
        $disque = Get-Partition -DriveLetter $lettre -ErrorAction Stop | Get-Disk -ErrorAction Stop | Select-Object -First 1
        $attributs.Add([string]$disque.SerialNumber)
    } catch { $attributs.Add('') }

    $brut = ($attributs | ForEach-Object { ([string]$_).Trim().ToLowerInvariant() }) -join '|'
    $sha = [System.Security.Cryptography.SHA256]::Create()
    try {
        $empreinte = $sha.ComputeHash([System.Text.Encoding]::UTF8.GetBytes($brut))
    } finally {
        $sha.Dispose()
    }
    return (($empreinte | ForEach-Object { $_.ToString('x2') }) -join '')
}

if ($MyInvocation.InvocationName -ne '.') {
    Write-Output (Get-YelenHostId)
}
