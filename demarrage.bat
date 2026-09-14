@echo off
setlocal
chcp 65001 >nul 2>&1
cd /d "%~dp0"

rem Installation et démarrage local YELEN SCHOOL.
rem PostgreSQL, Redis et les données sont gérés par Docker.
call "%~dp0installer\install-windows.bat" %*
exit /b %ERRORLEVEL%
