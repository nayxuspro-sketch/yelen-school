@echo off
setlocal
cd /d "%~dp0"

rem Active le HTTPS de YELEN SCHOOL sur le réseau local (certificats, pare-feu, proxy).
rem Exemples : activer-https.bat   |   activer-https.bat -Port 9443   |   activer-https.bat -Desactiver

net session >nul 2>&1
if not "%ERRORLEVEL%"=="0" (
    echo.
    echo Ce script doit etre lance en tant qu'administrateur.
    echo Faites un clic droit dessus puis choisissez "Executer en tant qu'administrateur".
    pause
    exit /b 1
)

powershell.exe -NoProfile -ExecutionPolicy Bypass ^
  -File "%~dp0installer\activer-https.ps1" %*
set "EXIT_CODE=%ERRORLEVEL%"

if "%EXIT_CODE%"=="0" (
    echo.
    echo Operation terminee.
    echo Consultez les instructions ci-dessus pour les postes.
) else (
    echo.
    echo Echec de l'activation du HTTPS (details ci-dessus).
    pause
)

exit /b %EXIT_CODE%
