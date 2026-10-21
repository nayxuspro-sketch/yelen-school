@echo off
setlocal
cd /d "%~dp0"

rem Programme la surveillance YELEN SCHOOL (toutes les 5 minutes) avec alerte SMS.
rem Exemple : programmer-surveillance.bat -Minutes 10

net session >nul 2>&1
if not "%ERRORLEVEL%"=="0" (
    echo.
    echo Ce script doit etre lance en tant qu'administrateur.
    echo Faites un clic droit dessus puis choisissez "Executer en tant qu'administrateur".
    pause
    exit /b 1
)

powershell.exe -NoProfile -ExecutionPolicy Bypass ^
  -File "%~dp0installer\register-watchdog-task.ps1" %*
set "EXIT_CODE=%ERRORLEVEL%"

if "%EXIT_CODE%"=="0" (
    echo.
    echo Surveillance configuree.
    echo Journal : logs\surveillance.log
) else (
    echo.
    echo Echec de la programmation de la surveillance.
    pause
)

exit /b %EXIT_CODE%
