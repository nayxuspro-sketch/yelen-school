@echo off
setlocal
chcp 65001 >nul 2>&1
cd /d "%~dp0"

rem Verifie la derniere sauvegarde de YELEN SCHOOL dans une base jetable (sans toucher aux donnees de l'ecole).
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0installer\tester-restauration.ps1" %*
set "EXIT_CODE=%ERRORLEVEL%"
echo.
pause
exit /b %EXIT_CODE%
