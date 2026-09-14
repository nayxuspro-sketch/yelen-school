@echo off
setlocal
chcp 65001 >nul 2>&1
cd /d "%~dp0.."

powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0install-windows.ps1" %*
set "EXIT_CODE=%ERRORLEVEL%"

if not "%EXIT_CODE%"=="0" (
    echo.
    echo Installation echouee. Consultez le message ci-dessus.
    pause
)

exit /b %EXIT_CODE%
