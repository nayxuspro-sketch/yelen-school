#requires -Version 5.1
<##
.SYNOPSIS
    Vérifie auprès de CinetPay les paiements Mobile Money en ligne en attente (toutes les 10 minutes).

.DESCRIPTION
    Script appelé par la tâche planifiée (register-mobile-money-task.ps1). Sans clés CinetPay
    dans .env ou sans Docker Desktop, il se termine silencieusement. Journal : logs\paiements-en-ligne.log.
#>
[CmdletBinding()]
param(
    [string]$TaskLog = ''
)

$ErrorActionPreference = 'Stop'
$Root = [System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))
$ComposeFile = Join-Path $Root 'docker-compose.client.yml'
$EnvFile = Join-Path $Root '.env'
$LogDirectory = Join-Path $Root 'logs'
if ([string]::IsNullOrWhiteSpace($TaskLog)) {
    $TaskLog = Join-Path $LogDirectory 'paiements-en-ligne.log'
}

function Write-Log {
    param([string]$Message)
    Add-Content -LiteralPath $TaskLog -Value "$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') $Message" -Encoding UTF8
}

try {
    New-Item -ItemType Directory -Path $LogDirectory -Force | Out-Null
    if (-not (Test-Path $EnvFile) -or -not (Test-Path $ComposeFile)) { exit 0 }
    $cle = Get-Content $EnvFile | Where-Object { $_ -match '^CINETPAY_API_KEY=\S+' } | Select-Object -First 1
    if ($null -eq $cle) { exit 0 }
    if (-not (Get-Command docker -ErrorAction SilentlyContinue)) { exit 0 }
    Set-Location $Root
    & docker info *> $null
    if ($LASTEXITCODE -ne 0) { exit 0 }

    $sortie = & docker compose -f $ComposeFile exec -T web python manage.py verifier_paiements_mobiles 2>&1
    $code = $LASTEXITCODE
    $sortie | ForEach-Object { Write-Log $_ }
    if ($code -ne 0) { Write-Log "ERREUR : la commande verifier_paiements_mobiles a renvoyé le code $code." }
    exit 0
} catch {
    try { Write-Log "ERREUR : $($_.Exception.Message)" } catch { Write-Error $_.Exception.Message }
    exit 1
}
