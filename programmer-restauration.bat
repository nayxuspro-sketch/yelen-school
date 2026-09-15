@echo off
setlocal
cd /d "%~dp0"

rem Programme une restauration UNIQUE et destructive a l'heure demandee.
rem Usage : programmer-restauration.bat "backups\fichier.dump" HH:MM CONFIRMER

if "%~1"=="" goto usage
if "%~2"=="" goto usage
if /I not "%~3"=="CONFIRMER" goto confirmation

net session >nul 2>&1
if not "%ERRORLEVEL%"=="0" (
    echo.
    echo Ce script doit etre lance en tant qu'administrateur.
    echo Faites un clic droit dessus puis choisissez "Executer en tant qu'administrateur".
    pause
    exit /b 1
)

powershell.exe -NoProfile -ExecutionPolicy Bypass ^
  -File "%~dp0installer\register-restore-task.ps1" ^
  -BackupFile "%~1" -Time "%~2" -ConfirmRestore
set "EXIT_CODE=%ERRORLEVEL%"

if "%EXIT_CODE%"=="0" (
    echo.
    echo Restauration unique programmee.
    echo Verifiez la tache dans le Planificateur de taches Windows.
) else (
    echo.
    echo Echec de la programmation de la restauration.
    pause
)

exit /b %EXIT_CODE%

:confirmation
echo.
echo ATTENTION : la restauration remplacera la base et les medias actuels.
echo Cette operation est programmee une seule fois et est irreversible sans sauvegarde.
echo.
echo Usage : %~nx0 "backups\fichier.dump" HH:MM CONFIRMER
echo Exemple: %~nx0 "backups\yelen_school_20260914_220000.dump" 03:00 CONFIRMER
pause
exit /b 2

:usage
echo.
echo Usage : %~nx0 "backups\fichier.dump" HH:MM CONFIRMER
echo Exemple: %~nx0 "backups\yelen_school_20260914_220000.dump" 03:00 CONFIRMER
pause
exit /b 2
