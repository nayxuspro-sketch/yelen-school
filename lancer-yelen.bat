@echo off
setlocal
chcp 65001 >nul 2>&1
cd /d "%~dp0"

rem Lance l'installation locale idempotente et ouvre YELEN SCHOOL.
call "%~dp0installer\install-windows.bat" %*
exit /b %ERRORLEVEL%
