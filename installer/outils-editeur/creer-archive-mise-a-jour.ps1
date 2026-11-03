#requires -Version 5.1
<##
.SYNOPSIS
    Crée l'archive de mise à jour hors ligne d'une version de YELEN SCHOOL (éditeur).

.DESCRIPTION
    Produit deux fichiers à remettre à l'école (clé USB, e-mail, WeTransfer) :
      yelen-school-<version>.bundle          historique complet + arbre de la branche main
      yelen-school-<version>.bundle.sha256   empreinte qui prouve que le fichier est intact

    L'école applique ensuite la mise à jour avec :
      C:\YELEN-SCHOOL\mettre-a-jour.bat -DepuisArchive chemin\yelen-school-<version>.bundle

    L'archive est un bundle git : aucune donnée de l'école n'y figure, seulement le code publié.
    À créer depuis un clone à jour de la branche main, après le commit et le tag de la version.

.EXAMPLE
    .\creer-archive-mise-a-jour.ps1 -Sortie D:\livraisons

.EXAMPLE
    .\creer-archive-mise-a-jour.ps1 -Sortie D:\livraisons -SansHistorique
    (archive plus légère, valable seulement si l'école a déjà la même généalogie)
#>

[CmdletBinding()]
param(
    [string]$Sortie = '',
    [switch]$SansHistorique
)

$ErrorActionPreference = 'Stop'
$Root = [System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot '../..'))
$Branche = 'main'

function Fail {
    param([string]$Message)
    throw $Message
}

if (-not (Get-Command git -ErrorAction SilentlyContinue)) { Fail 'git est introuvable dans le PATH.' }
if ((& git -C $Root rev-parse --is-inside-work-tree 2>$null) -ne 'true') {
    Fail "$Root n'est pas un dépôt git."
}
# Seules les modifications de fichiers SUIVIS comptent : un fichier non suivi ne part jamais dans le bundle.
$sales = (& git -C $Root status --porcelain --untracked-files=no | Out-String).Trim()
if ($sales) { Fail "Le dépôt contient des modifications non validées :`n$sales" }

$version = (& git -C $Root show "${Branche}:VERSION" 2>$null | Out-String).Trim()
if ([string]::IsNullOrWhiteSpace($version)) { Fail "Impossible de lire VERSION sur la branche $Branche." }
$commit = (& git -C $Root rev-parse --short $Branche | Out-String).Trim()

if ([string]::IsNullOrWhiteSpace($Sortie)) { $Sortie = $Root }
if (-not (Test-Path -LiteralPath $Sortie)) { New-Item -ItemType Directory -Path $Sortie -Force | Out-Null }
$Sortie = (Resolve-Path -LiteralPath $Sortie).Path

$nom = "yelen-school-$version.bundle"
$archive = Join-Path $Sortie $nom
$fichierEmpreinte = "$archive.sha256"
Remove-Item -LiteralPath $archive, $fichierEmpreinte -Force -ErrorAction SilentlyContinue

if ($SansHistorique) {
    $arguments = @('-C', $Root, 'bundle', 'create', $archive, $Branche)
} else {
    $arguments = @('-C', $Root, 'bundle', 'create', $archive, '--all')
}
& git @arguments
if ($LASTEXITCODE -ne 0) { Fail 'La création du bundle a échoué.' }

& git -C $Root bundle verify $archive *> $null
if ($LASTEXITCODE -ne 0) { Fail 'Le bundle créé ne passe pas la vérification : ne pas le livrer.' }

$empreinte = (Get-FileHash -LiteralPath $archive -Algorithm SHA256).Hash.ToLower()
# Format lisible par `sha256sum -c` et par mettre-a-jour.ps1 (premier champ = empreinte).
Set-Content -LiteralPath $fichierEmpreinte -Value "$empreinte  $nom" -Encoding ASCII
$taille = [math]::Round((Get-Item -LiteralPath $archive).Length / 1MB, 1)

Write-Host ''
Write-Host "Archive prête pour la version $version ($commit) :" -ForegroundColor Green
Write-Host "  $archive"
Write-Host "  $fichierEmpreinte"
Write-Host "  Taille : $taille Mo"
Write-Host "  SHA-256 : $empreinte"
Write-Host ''
Write-Host "À l'école : copier les DEUX fichiers ensemble, puis dans un cmd :" -ForegroundColor Cyan
Write-Host "  cd /d C:\YELEN-SCHOOL"
Write-Host "  mettre-a-jour.bat -DepuisArchive $nom"
Write-Host ''
Write-Host "Communiquer l'empreinte par un autre canal que le fichier (téléphone, SMS) :" -ForegroundColor DarkGray
Write-Host "c'est elle qui prouve que l'archive n'a pas été altérée en route."
