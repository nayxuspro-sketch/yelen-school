@echo off
setlocal
cd /d "%~dp0"

rem Programme la sauvegarde quotidienne PostgreSQL et médias YELEN SCHOOL.
rem Heure par défaut : 22:00. Exemple : programmer-sauvegarde.bat 23:30

net session >nul 2>&1
if not "%ERRORLEVEL%"=="0" (
    echo.
    echo Ce script doit etre lance en tant qu'administrateur.
    echo Faites un clic droit dessus puis choisissez "Executer en tant qu'administrateur".
    pause
    exit /b 1
)

powershell.exe -NoProfile -ExecutionPolicy Bypass ^
  -File "%~dp0installer\register-backup-task.ps1" %*
set "EXIT_CODE=%ERRORLEVEL%"

if "%EXIT_CODE%"=="0" (
    echo.
    echo Sauvegarde automatique configuree.
    echo Testez-la depuis le Planificateur de taches Windows.
) else (
    echo.
    echo Echec de la programmation de la sauvegarde.
    pause
)

exit /b %EXIT_CODE%
