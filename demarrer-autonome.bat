@echo off
setlocal enabledelayedexpansion
chcp 65001 >nul 2>&1
cd /d "%~dp0"
title YELEN SCHOOL - Serveur (mode autonome)

echo ============================================================
echo   YELEN SCHOOL - Demarrage du serveur (mode autonome SQLite)
echo ============================================================
echo.

:: ------------------------------------------------------------------
:: 1. Python
:: ------------------------------------------------------------------
where python >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo [ERREUR] Python introuvable. Installez Python 3.11+ depuis https://www.python.org
    echo          ^(cochez "Add python.exe to PATH" pendant l'installation^)
    pause & exit /b 1
)
for /f "tokens=2" %%v in ('python --version 2^>^&1') do set PYVER=%%v
echo [OK] Python %PYVER%

:: ------------------------------------------------------------------
:: 2. Fichier .env (cree au premier lancement : cle secrete + IP du serveur)
:: ------------------------------------------------------------------
set LANIP=
for /f "tokens=2 delims=:" %%i in ('ipconfig ^| findstr /c:"IPv4" ^| findstr /v "127.0.0.1"') do if not defined LANIP set LANIP=%%i
set LANIP=!LANIP: =!
if not exist ".env" (
    copy /y ".env.autonome.example" ".env" >nul
    for /f "delims=" %%k in ('python -c "import secrets;print(secrets.token_urlsafe(64))"') do set NEWKEY=%%k
    powershell -NoProfile -Command "(Get-Content .env) -replace 'SECRET_KEY=CHANGEZ-MOI.*', 'SECRET_KEY=!NEWKEY!' | Set-Content .env"
    if defined LANIP powershell -NoProfile -Command "(Get-Content .env) -replace '192\.168\.1\.10', '!LANIP!' | Set-Content .env"
    echo [OK] Fichier .env cree a partir de .env.autonome.example ^(cle secrete generee, IP serveur !LANIP!^)
    echo      Si l'IP du serveur change, mettez a jour ALLOWED_HOSTS / CSRF_TRUSTED_ORIGINS dans .env.
)

:: Controle anti-copie : sans effet tant que SERVER_HARDWARE_UUID n'est pas defini dans .env
if exist "installer\verifier-integrite-anti-copie.bat" (
    call "installer\verifier-integrite-anti-copie.bat"
    if errorlevel 1 (
        echo [ERREUR] Controle d'integrite anti-copie echoue. Contactez l'editeur.
        pause & exit /b 1
    )
)

:: ------------------------------------------------------------------
:: 3. Environnement virtuel + dependances
:: ------------------------------------------------------------------
if not exist ".venv\Scripts\python.exe" (
    echo [1/5] Creation de l'environnement Python...
    python -m venv .venv || (echo [ERREUR] Creation du venv impossible & pause & exit /b 1)
)
call .venv\Scripts\activate.bat
if not exist ".venv\.deps_ok" (
    echo [2/5] Installation des dependances ^(une seule fois, quelques minutes^)...
    python -m pip install --upgrade pip -q
    pip install -r requirements\base.txt -q || (echo [ERREUR] Installation des dependances echouee & pause & exit /b 1)
    echo ok > .venv\.deps_ok
) else (
    echo [2/5] Dependances deja installees
)

:: ------------------------------------------------------------------
:: 4. Base de donnees, cache, fichiers statiques, admin
:: ------------------------------------------------------------------
set DB_ENGINE=sqlite
echo [3/5] Mise a jour de la base de donnees...
python manage.py migrate --noinput || (echo [ERREUR] Migration echouee & pause & exit /b 1)
python manage.py createcachetable >nul 2>&1
echo [4/5] Fichiers statiques...
python manage.py collectstatic --noinput >nul 2>&1
findstr /i "ENSURE_ADMIN=true" .env >nul 2>&1 && python manage.py ensure_admin

:: ------------------------------------------------------------------
:: 5. Lancement du serveur web (Waitress - production Windows)
:: ------------------------------------------------------------------
set PORT=8000
set WEB_THREADS=8
for /f "tokens=1,2 delims==" %%a in ('findstr /r "^PORT= ^WEB_THREADS=" .env') do set %%a=%%b

:: Pare-feu Windows : regle entrante pour le port (necessite des droits administrateur)
netsh advfirewall firewall show rule name="YELEN SCHOOL port !PORT!" >nul 2>&1
if errorlevel 1 netsh advfirewall firewall add rule name="YELEN SCHOOL port !PORT!" dir=in action=allow protocol=TCP localport=!PORT! >nul 2>&1
netsh advfirewall firewall show rule name="YELEN SCHOOL port !PORT!" >nul 2>&1
if errorlevel 1 (echo [INFO] Pare-feu : autorisez le port !PORT! en entree [TCP], ou relancez ce script en administrateur) else (echo [OK] Pare-feu : port !PORT! autorise)

echo [5/5] Demarrage du serveur web...
echo.
echo ============================================================
echo   Serveur pret. Acces depuis les postes de l'ecole :
echo.
echo       http://!LANIP!:!PORT!
echo.
echo   Sur ce poste :   http://localhost:!PORT!
echo   Laissez cette fenetre ouverte. Ctrl+C pour arreter.
echo ============================================================
echo.
start "" "http://localhost:!PORT!/accounts/login/"
waitress-serve --listen=0.0.0.0:!PORT! --threads=!WEB_THREADS! --channel-timeout=120 yelen_school.wsgi:application
pause
