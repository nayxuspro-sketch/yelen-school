@echo off
setlocal
cd /d "%~dp0"

rem Ouvre l'acces a distance (Internet) au portail parents par un tunnel Cloudflare.
rem Prerequis : tunnel cree dans Cloudflare Zero Trust, nom public et jeton disponibles.
rem Exemples : activer-acces-distance.bat
rem             activer-acces-distance.bat -Jeton "eyJhIjoi..."
rem             activer-acces-distance.bat -Domaine bureau.tail1234.ts.net:8443 -EnvSeulement
rem             activer-acces-distance.bat -Desactiver

net session >nul 2>&1
if not "%ERRORLEVEL%"=="0" (
    echo.
    echo Ce script doit etre lance en tant qu'administrateur.
    echo Faites un clic droit dessus puis choisissez "Executer en tant qu'administrateur".
    pause
    exit /b 1
)

powershell.exe -NoProfile -ExecutionPolicy Bypass ^
  -File "%~dp0installer\activer-acces-distance.ps1" %*
set "EXIT_CODE=%ERRORLEVEL%"

if "%EXIT_CODE%"=="0" (
    echo.
    echo Operation terminee.
    rem La consigne de redemarrage depend du mode (Docker : demarrage.bat ; autonome :
    rem demarrer-autonome.bat) : elle est affichee juste au-dessus par le script PowerShell.
    echo Pour appliquer le fichier .env, redemarrez l'application ^(consigne ci-dessus^).
) else (
    echo.
    echo Echec de l'acces a distance ^(details ci-dessus^).
    pause
)

exit /b %EXIT_CODE%
