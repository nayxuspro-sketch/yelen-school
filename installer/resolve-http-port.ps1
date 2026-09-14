#requires -Version 5.1
<##
.SYNOPSIS
    Sélectionne un port HTTP local libre pour YELEN SCHOOL.

.DESCRIPTION
    Ce fichier est destiné à être chargé par les scripts d'installation et de
    démarrage automatique. Il ne lance aucune action lors du chargement.
    Le port configuré est conservé s'il est libre ou déjà utilisé par un
    conteneur YELEN SCHOOL. Sinon, les ports documentés 8000 à 8005 sont testés.
#>

function Test-YelenTcpPortAvailable {
    param(
        [Parameter(Mandatory = $true)]
        [ValidateRange(1, 65535)]
        [int]$Port
    )

    $listener = $null
    try {
        $listener = New-Object -TypeName System.Net.Sockets.TcpListener -ArgumentList @(
            [System.Net.IPAddress]::Loopback,
            $Port
        )
        $listener.Start()
        return $true
    } catch {
        return $false
    } finally {
        if ($null -ne $listener) {
            try { $listener.Stop() } catch { }
        }
    }
}

function Test-YelenContainerPortInUse {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Root,

        [Parameter(Mandatory = $true)]
        [string]$ComposeFile,

        [Parameter(Mandatory = $true)]
        [ValidateRange(1, 65535)]
        [int]$Port
    )

    $published = @()
    $composeExitCode = 1
    Push-Location $Root
    try {
        # 8000 est le port interne du conteneur web. Compose renvoie ici le
        # port publié réellement utilisé par YELEN SCHOOL.
        $published = @(& docker compose -f $ComposeFile port web 8000 2>$null)
        $composeExitCode = $LASTEXITCODE
    } catch {
        return $false
    } finally {
        Pop-Location
    }

    if ($composeExitCode -ne 0) {
        return $false
    }

    return [bool]($published | Where-Object {
        $_.ToString().Trim() -match "(^|:)$Port$"
    })
}

function Select-YelenHttpPort {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Root,

        [Parameter(Mandatory = $true)]
        [string]$ComposeFile,

        [Parameter(Mandatory = $true)]
        [ValidateRange(1, 65535)]
        [int]$PreferredPort
    )

    # Le port configuré reste prioritaire. Les ports 8000 à 8005 constituent
    # la plage de repli documentée pour les installations client.
    $candidatePorts = @($PreferredPort) + @(8000..8005)
    $candidatePorts = @($candidatePorts | Select-Object -Unique)

    foreach ($candidate in $candidatePorts) {
        # Lors d'un redémarrage, ne pas déplacer une instance YELEN déjà active.
        if (Test-YelenContainerPortInUse -Root $Root -ComposeFile $ComposeFile -Port $candidate) {
            return [int]$candidate
        }
        if (Test-YelenTcpPortAvailable -Port $candidate) {
            return [int]$candidate
        }
    }

    throw 'Aucun port disponible dans la plage YELEN SCHOOL (8000 à 8005). Libérez un port ou définissez un autre YELEN_HTTP_PORT dans .env.'
}
