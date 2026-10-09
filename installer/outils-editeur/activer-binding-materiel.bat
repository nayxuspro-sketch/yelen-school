@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion

echo ================================================================
echo   YELEN SCHOOL — ENRÔLEMENT DU MATÉRIEL SERVEUR (ANTI-PIRATAGE)
echo ================================================================
echo.

:: 1. Vérification des droits Administrateur
net session >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERREUR] Ce script nécessite les droits Administrateur.
    echo Clic droit sur ce fichier puis "Exécuter en tant qu'administrateur".
    echo.
    pause
    exit /b 1
)

:: 2. Détection de la racine YELEN SCHOOL (par défaut C:\YELEN-SCHOOL ou dossier parent si exécuté depuis installer\)
set "ROOT_DIR=C:\YELEN-SCHOOL"
if not exist "%ROOT_DIR%\.env" (
    set "PARENT_DIR=%~dp0.."
    pushd "!PARENT_DIR!"
    if exist ".env" set "ROOT_DIR=!CD!"
    popd
)

if not exist "%ROOT_DIR%\.env" (
    echo [ERREUR] Impossible de trouver le dossier YELEN SCHOOL avec le fichier .env
    echo Vérifiez que l'application est bien installée dans C:\YELEN-SCHOOL
    echo.
    pause
    exit /b 1
)

echo Dossier serveur détecté : %ROOT_DIR%
echo.

echo [1/3] Extraction des identifiants matériels uniques du PC client...
set "SYS_UUID="
set "CPU_ID="
set "DISK_SERIAL="

for /f "skip=1 tokens=*" %%A in ('wmic csproduct get uuid 2^>nul') do (
    if not defined SYS_UUID if not "%%A"=="" set "SYS_UUID=%%A"
)
for /f "skip=1 tokens=*" %%B in ('wmic cpu get processorid 2^>nul') do (
    if not defined CPU_ID if not "%%B"=="" set "CPU_ID=%%B"
)
for /f "skip=1 tokens=*" %%C in ('wmic diskdrive get serialnumber 2^>nul') do (
    if not defined DISK_SERIAL if not "%%C"=="" set "DISK_SERIAL=%%C"
)

set "SYS_UUID=!SYS_UUID: =!"
set "CPU_ID=!CPU_ID: =!"
set "DISK_SERIAL=!DISK_SERIAL: =!"

if "!SYS_UUID!"=="" (
    echo [ERREUR] Impossible de lire l'UUID de la carte mère.
    pause
    exit /b 1
)

echo - UUID Carte mère : !SYS_UUID!
echo - ID Processeur   : !CPU_ID!
echo - Série Disque    : !DISK_SERIAL!
echo.

echo [2/3] Verrouillage matériel dans la configuration locale (.env)...
powershell -NoProfile -Command ^
    "$envPath = '%ROOT_DIR%\.env';" ^
    "$lines = Get-Content -Path $envPath -Encoding UTF8 | Where-Object { $_ -notmatch '^(SERVER_HARDWARE_UUID|SERVER_CPU_ID|SERVER_DISK_SERIAL|LICENSE_ENFORCEMENT|LICENCE_ANTITAMPER_ENABLED)=' };" ^
    "$lines += '';" ^
    "$lines += '# Verrouillage matériel anti-copie (généré lors du déploiement)';" ^
    "$lines += 'SERVER_HARDWARE_UUID=!SYS_UUID!';" ^
    "$lines += 'SERVER_CPU_ID=!CPU_ID!';" ^
    "$lines += 'SERVER_DISK_SERIAL=!DISK_SERIAL!';" ^
    "$lines += 'LICENSE_ENFORCEMENT=true';" ^
    "$lines += 'LICENCE_ANTITAMPER_ENABLED=true';" ^
    "$utf8NoBom = New-Object System.Text.UTF8Encoding($false);" ^
    "[System.IO.File]::WriteAllLines($envPath, $lines, $utf8NoBom);"

echo.
echo [3/3] Contrôle de cohérence...
findstr /i "SERVER_HARDWARE_UUID" "%ROOT_DIR%\.env" >nul
if %errorlevel% equ 0 (
    echo [SUCCÈS] Empreinte matérielle enregistrée et verrouillée dans .env.
) else (
    echo [ERREUR] Échec de l'écriture dans le fichier .env.
    pause
    exit /b 1
)

echo.
echo ================================================================
echo   ✅ Le serveur YELEN SCHOOL est désormais lié à cette machine !
echo   ⚠️ RAPPEL DE SÉCURITÉ :
echo   Supprimez ce script de la machine du client (gardez-le sur
echo   votre clé USB d'installateur).
echo ================================================================
echo.
pause
