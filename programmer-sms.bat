@echo off
setlocal
cd /d "%~dp0"

rem Programme l'envoi quotidien des SMS automatiques.
rem Heure par defaut : 07:00. Exemple : programmer-sms.bat 08:00

net session >nul 2>&1
if not "%ERRORLEVEL%"=="0" (
    echo.
    echo Ce script doit etre lance en tant qu'administrateur.
    echo Faites un clic droit dessus puis choisissez "Executer en tant qu'administrateur".
    pause
    exit /b 1
)

powershell.exe -NoProfile -ExecutionPolicy Bypass ^
  -File "%~dp0installer\register-sms-task.ps1" %*
set "EXIT_CODE=%ERRORLEVEL%"

if "%EXIT_CODE%"=="0" (
    echo.
    echo SMS automatiques configures.
    echo Testez-les depuis le Planificateur de taches Windows.
) else (
    echo.
    echo Echec de la programmation des SMS automatiques.
    pause
)

exit /b %EXIT_CODE%
