@echo off
setlocal
chcp 65001 >nul 2>&1
cd /d "%~dp0"

rem Cree ou remet a niveau l'environnement de test YELEN-TEST (a cote de ce dossier) : meme version
rem que la production, copie de la derniere sauvegarde, controle des licences actif. Production intacte.
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0installer\creer-environnement-test.ps1" -OuvrirNavigateur %*
set "EXIT_CODE=%ERRORLEVEL%"
echo.
pause
exit /b %EXIT_CODE%
