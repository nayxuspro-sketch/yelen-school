@echo off
setlocal enabledelayedexpansion
chcp 65001 >nul 2>&1
cd /d "%~dp0"

echo ^>^>^> YELEN SCHOOL - Demarrage rapide
echo.

:: ------------------------------------------------------------------
:: 1. Verification Docker
:: ------------------------------------------------------------------
where docker >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo [ERREUR] Docker introuvable.
    echo          https://www.docker.com/products/docker-desktop/
    pause & exit /b 1
)

:: ------------------------------------------------------------------
:: 2. Demarrage conteneurs (silencieux)
:: ------------------------------------------------------------------
echo [1/3] Demarrage des conteneurs...
docker compose -f docker-compose.dev.yml up -d --build >nul 2>&1
if !ERRORLEVEL! neq 0 (
    echo [ERREUR] Echec au demarrage.
    pause & exit /b 1
)
echo [OK] Conteneurs demarres

:: ------------------------------------------------------------------
:: 3. Attente du serveur (avec progression toutes les 10s)
:: ------------------------------------------------------------------
echo.
echo [2/3] Attente du serveur web...
set "URL=http://localhost:8000/accounts/login/"
set "RETRIES=0"

:wait_loop
set /a RETRIES+=1
if !RETRIES! gtr 60 (
    echo.
    echo [ERREUR] Serveur injoignable apres 60s.
    pause & exit /b 1
)
>nul 2>&1 curl -s -o nul -w "%%{http_code}" "!URL!" | findstr "200 301 302 401 403"
if !ERRORLEVEL! equ 0 goto pret
>nul 2>&1 powershell -NoProfile -Command "try{ (Invoke-WebRequest '!URL!' -UseBasicParsing -TimeoutSec 2).StatusCode -match '200|301|302|401|403' }catch{exit 1}"
if !ERRORLEVEL! equ 0 goto pret
>nul ping -n 2 127.0.0.1
set /a "REPONSE=!RETRIES! %% 10"
if !REPONSE! equ 0 <nul set /p "=. Attente... !RETRIES!s"
goto wait_loop

:pret
echo.
echo [OK] Serveur web pret

:: ------------------------------------------------------------------
:: 4. Ouverture navigateur
:: ------------------------------------------------------------------
echo.
echo [3/3] Ouverture du navigateur...
powershell -NoProfile -Command "Start-Process '!URL!'" >nul 2>&1
if !ERRORLEVEL! equ 0 (
    echo [OK] Navigateur ouvert
) else (
    echo.
    echo ==^> Copiez ce lien dans votre navigateur :
    echo    !URL!
)
echo.
echo ^>^>^> YELEN SCHOOL operationnel
echo Fermeture automatique dans 3 secondes...
>nul ping -n 4 127.0.0.1
exit /b 0
