@echo off

:: --- Reduction de la fenetre apres lancement ---
if "%YELEN_RUNNING%"=="" (
    set YELEN_RUNNING=1
    start "" /min "%~dpnx0"
    exit
)

chcp 65001 >nul
setlocal enabledelayedexpansion

:: --- Chemins ---
set "SCRIPT_DIR=%~dp0"
cd /d "%SCRIPT_DIR%"

echo ^>^>^> YELEN SCHOOL - Demarrage de l'application
echo.

:: --- Verifier que Docker est installe ---
where docker >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo [ERREUR] Docker n'est pas installe ou introuvable.
    echo          Installez Docker Desktop depuis https://www.docker.com/products/docker-desktop/
    pause
    exit 1
)

:: --- Verifier que le moteur Docker tourne ---
docker info >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo [ERREUR] Le moteur Docker n'est pas en cours d'execution.
    echo          Lancez Docker Desktop et reessayez.
    pause
    exit 1
)

:: --- Construire et lancer les services ---
echo [1/3] Construction et demarrage des conteneurs...
docker compose -f docker-compose.dev.yml up -d --build
if %ERRORLEVEL% neq 0 (
    echo [ERREUR] Le demarrage des conteneurs a echoue.
    pause
    exit 1
)
echo       OK
echo.

:: --- Attendre que le serveur web reponde ---
echo [2/3] Attente du serveur web (cela peut prendre 30 a 60 secondes)...
set "RETRIES=0"
:wait_loop
curl -s -o nul -w "%%{http_code}" http://localhost:8000/ 2>nul | findstr "200 302 401" >nul 2>&1
if !ERRORLEVEL! equ 0 goto server_ready
set /a RETRIES+=1
if !RETRIES! geq 30 (
    echo [ATTENTION] Le serveur Web n'a pas repondu a temps.
    echo             Verifiez l'etat dans Docker Desktop.
    pause
    exit 1
)
ping -n 3 127.0.0.1 >nul
goto wait_loop

:server_ready
echo       Serveur pret apres !RETRIES!*2 secondes
echo.

:: --- Ouvrir le navigateur ---
echo [3/3] Ouverture du navigateur...
start http://localhost:8000/accounts/login/?next=/
echo       Application lancee sur http://localhost:8000
echo.

echo ^>^>^> YELEN SCHOOL est operationnel.
exit
