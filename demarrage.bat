@echo off
if exist "%~dp0installer\verifier-integrite-anti-copie.bat" (
    call "%~dp0installer\verifier-integrite-anti-copie.bat"
    if errorlevel 1 exit /b 1
)
setlocal
chcp 65001 >nul 2>&1
cd /d "%~dp0"

call "%~dp0installer\install-windows.bat" %*
exit /b %ERRORLEVEL%
