@echo off
setlocal
cd /d "%~dp0"

rem Programme le démarrage automatique de YELEN SCHOOL à l'ouverture de session Windows.

net session >nul 2>&1
if not "%ERRORLEVEL%"=="0" (
    echo.
    echo Ce script doit etre lance en tant qu'administrateur.
    echo Faites un clic droit dessus puis choisissez "Executer en tant qu'administrateur".
    pause
    exit /b 1
)

powershell.exe -NoProfile -ExecutionPolicy Bypass ^
  -File "%~dp0installer\register-startup-task.ps1"
set "EXIT_CODE=%ERRORLEVEL%"

if "%EXIT_CODE%"=="0" (
    echo.
    echo Demarrage automatique configure.
    echo Docker Desktop doit etre configure pour demarrer avec Windows.
) else (
    echo.
    echo Echec de la programmation du demarrage automatique.
    pause
)

exit /b %EXIT_CODE%
