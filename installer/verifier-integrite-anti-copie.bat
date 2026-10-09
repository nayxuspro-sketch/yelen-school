@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion

:: Détection de la racine de l'application
set "ROOT_DIR=C:\YELEN-SCHOOL"
if not exist "%ROOT_DIR%\.env" (
    set "PARENT_DIR=%~dp0.."
    pushd "!PARENT_DIR!"
    if exist ".env" set "ROOT_DIR=!CD!"
    popd
)

if not exist "%ROOT_DIR%\.env" (
    echo [ERREUR] Configuration .env introuvable dans %ROOT_DIR%
    exit /b 1
)

:: Récupération de l'UUID enregistré lors du déploiement
set "SAVED_UUID="
for /f "tokens=1,* delims==" %%A in ('type "%ROOT_DIR%\.env" ^| findstr "^SERVER_HARDWARE_UUID="') do (
    set "SAVED_UUID=%%B"
)

:: Si aucun binding n'a été appliqué, laisser passer (mode démo/dev)
if not defined SAVED_UUID (
    exit /b 0
)

:: Récupération de l'UUID physique actuel de la machine
set "CURRENT_UUID="
for /f "skip=1 tokens=*" %%A in ('wmic csproduct get uuid 2^>nul') do (
    if not defined CURRENT_UUID if not "%%A"=="" set "CURRENT_UUID=%%A"
)
set "CURRENT_UUID=!CURRENT_UUID: =!"
set "SAVED_UUID=!SAVED_UUID: =!"

:: Comparaison stricte
if /i not "!CURRENT_UUID!"=="!SAVED_UUID!" (
    echo.
    echo ================================================================
    echo   ⛔ VIOLATION DE LICENCE : COPIE ILLICITE DÉTECTÉE
    echo ================================================================
    echo Cette copie de YELEN SCHOOL a été déplacée sur une autre machine.
    echo.
    echo L'application est protégée et ne peut s'exécuter que sur le
    echo serveur physique autorisé lors du déploiement officiel.
    echo.
    echo Veuillez contacter l'éditeur YELEN SCHOOL pour régulariser.
    echo ================================================================
    echo.
    pause
    exit /b 2
)

exit /b 0
