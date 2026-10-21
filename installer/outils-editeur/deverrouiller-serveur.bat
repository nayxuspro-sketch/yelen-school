@echo off
chcp 65001 >nul
title YELEN SCHOOL - Deverrouillage du serveur (maintenance)
net session >nul 2>&1
if errorlevel 1 (
    echo [ERREUR] Clic droit sur ce fichier puis "Executer en tant qu administrateur".
    pause
    exit /b 1
)
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0deverrouiller-serveur.ps1" %*
set "CODE=%ERRORLEVEL%"
pause
exit /b %CODE%
