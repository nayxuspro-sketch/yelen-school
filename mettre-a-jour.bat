@echo off
setlocal
chcp 65001 >nul 2>&1
cd /d "%~dp0"

rem Met a jour YELEN SCHOOL (Docker) : sauvegarde, nouvelle version GitHub, reconstruction, redemarrage.
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0installer\mettre-a-jour.ps1" %*
set "EXIT_CODE=%ERRORLEVEL%"
echo.
pause
exit /b %EXIT_CODE%
