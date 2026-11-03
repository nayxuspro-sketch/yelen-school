#requires -Version 5.1
<##
.SYNOPSIS
     Utilitaires pour exécuter les tâches planifiées YELEN SCHOOL sans fenêtre console noire.
.DESCRIPTION
    Sous Windows 10/11 (en particulier Windows 11 avec Windows Terminal), lancer directement
    `powershell.exe -WindowStyle Hidden` depuis le Planificateur de tâches ouvre brièvement une
    fenêtre noire avant que PowerShell ne la masque. Passer par `conhost.exe --headless` attache
    PowerShell et tous ses processus enfants (git, docker) à une console sans fenêtre dès la création.
#>

function New-YelenHeadlessTaskAction {
    param(
        [Parameter(Mandatory = $true)]
        [string]$PowerShellArguments,
        [string]$WorkingDirectory = ''
    )

    $sysDir = [Environment]::SystemDirectory
    $conhost = Join-Path $sysDir 'conhost.exe'
    $psCandidate = Join-Path $sysDir 'WindowsPowerShell\v1.0\powershell.exe'
    $psExe = if (Test-Path -LiteralPath $psCandidate) { $psCandidate } else { 'powershell.exe' }

    if (Test-Path -LiteralPath $conhost) {
        $execute = $conhost
        $argument = "--headless `"$psExe`" $PowerShellArguments"
    } else {
        $execute = $psExe
        $argument = $PowerShellArguments
    }

    if ([string]::IsNullOrWhiteSpace($WorkingDirectory)) {
        return New-ScheduledTaskAction -Execute $execute -Argument $argument
    }
    return New-ScheduledTaskAction -Execute $execute -Argument $argument -WorkingDirectory $WorkingDirectory
}

function Update-YelenTasksHeadless {
    # Migre sur place toute tâche existante « YELEN SCHOOL - * » encore branchée directement sur
    # powershell.exe vers conhost.exe --headless, sans arrêter une exécution éventuellement en cours.
    if (-not (Get-Command Get-ScheduledTask -ErrorAction SilentlyContinue)) { return @() }

    $migrees = @()
    $taches = @(Get-ScheduledTask -TaskName 'YELEN SCHOOL - *' -ErrorAction SilentlyContinue)
    foreach ($tache in $taches) {
        if ($null -eq $tache.Actions -or $tache.Actions.Count -eq 0) { continue }
        $act = $tache.Actions[0]
        $nomExe = [System.IO.Path]::GetFileName([string]$act.Execute)
        if ($nomExe -ine 'powershell.exe') { continue }

        try {
            $nouvelleAction = New-YelenHeadlessTaskAction `
                -PowerShellArguments ([string]$act.Arguments) `
                -WorkingDirectory ([string]$act.WorkingDirectory)
            Set-ScheduledTask -TaskName $tache.TaskName -TaskPath $tache.TaskPath -Action $nouvelleAction -ErrorAction Stop | Out-Null
            $migrees += $tache.TaskName
        } catch {
            # Une tâche enregistrée avec RunLevel Highest exige une session Administrateur pour être modifiée.
        }
    }
    return $migrees
}
