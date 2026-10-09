@echo off
if exist "%~dp0installer\verifier-integrite-anti-copie.bat" (
    call "%~dp0installer\verifier-integrite-anti-copie.bat"
    if errorlevel 1 exit /b 1
)
setlocal enabledelayedexpansion
chcp 65001 >nul 2>&1
cd /d "%~dp0"

title YELEN SCHOOL - Mode Autonome (SQLite Réseau Local)
color 0B

echo =====================================================================
echo       YELEN SCHOOL - MODE AUTONOME SANS DOCKER (SQLITE)
echo            ACCÈS MULTI-POSTES EN RÉSEAU LOCAL (LAN)
echo =====================================================================
echo.

:: 1. Vérification de Python local
where python >nul 2>&1
if %ERRORLEVEL% neq 0 (
    color 0C
    echo [ERREUR] Python n'est pas installé sur cette machine ou n'est pas dans le PATH.
    echo          Veuillez installer Python 3.10+ depuis https://www.python.org/
    echo          (Pensez à cocher "Add Python to PATH" lors de l'installation).
    pause
    exit /b 1
)
echo [OK] Python détecté.

:: 2. Détection de l'adresse IP locale de la machine
for /f "tokens=4" %%a in ('route print ^| findstr 0.0.0.0 ^| findstr /v "0.0.0.0.*0.0.0.0"') do (
    set "LAN_IP=%%a"
)
if "%LAN_IP%"=="" (
    for /f "tokens=2 delims=:" %%a in ('ipconfig ^| findstr /i "IPv4" ^| findstr /v "127.0.0.1"') do (
        set "LAN_IP=%%a"
        set "LAN_IP=!LAN_IP: =!"
    )
)

:: 3. Configuration automatique du fichier .env pour SQLite & Réseau Local
if not exist ".env" (
    if exist ".env.example" (
        copy /y ".env.example" ".env" >nul
        echo [INFO] Fichier .env créé depuis .env.example.
    ) else (
        type nul > ".env"
    )
)

echo [INFO] Configuration du mode SQLite et des autorisations réseau dans .env...

powershell -NoProfile -Command ^
    "$envFile = '.env';" ^
    "$content = if (Test-Path $envFile) { Get-Content $envFile -Raw -Encoding UTF8 } else { '' };" ^
    "function Set-EnvVar($key, $val) {" ^
    "    if ($script:content -match ('(?m)^' + [regex]::Escape($key) + '=.*$')) {" ^
    "        $script:content = $script:content -replace ('(?m)^' + [regex]::Escape($key) + '=.*$'), ($key + '=' + $val);" ^
    "    } else {" ^
    "        $script:content += [Environment]::NewLine + ($key + '=' + $val);" ^
    "    }" ^
    "};" ^
    "Set-EnvVar 'DB_ENGINE' 'sqlite';" ^
    "Set-EnvVar 'SQLITE_PATH' 'data/yelen_school.sqlite3';" ^
    "Set-EnvVar 'CACHE_BACKEND' 'database';" ^
    "Set-EnvVar 'DEBUG' 'False';" ^
    "Set-EnvVar 'DISABLE_HTTPS_REDIRECT' 'true';" ^
    "if (-not ($content -match 'ALLOWED_HOSTS=')) {" ^
    "    Set-EnvVar 'ALLOWED_HOSTS' '*';" ^
    "} else {" ^
    "    Set-EnvVar 'ALLOWED_HOSTS' '*';" ^
    "};" ^
    "if (-not ($content -match 'SECRET_KEY=[a-zA-Z0-9]')) {" ^
    "    $rnd = [System.Guid]::NewGuid().ToString('N') + [System.Guid]::NewGuid().ToString('N');" ^
    "    Set-EnvVar 'SECRET_KEY' $rnd;" ^
    "};" ^
    "[System.IO.File]::WriteAllText($envFile, $script:content.Trim() + [Environment]::NewLine, [System.Text.Encoding]::UTF8);"

if not exist "data" mkdir "data"

echo [OK] .env configuré automatiquement (DB_ENGINE=sqlite, ALLOWED_HOSTS=*).
echo.

:: 4. Application des migrations de base de données
echo [1/3] Application des migrations SQLite...
python manage.py migrate --noinput
if %ERRORLEVEL% neq 0 (
    color 0C
    echo [ERREUR] Échec lors de la migration de la base SQLite.
    pause
    exit /b 1
)
echo [OK] Base SQLite prête dans data\yelen_school.sqlite3 (Mode WAL optimisé).

:: 5. Table de cache & Collecte des fichiers statiques
python manage.py createcachetable >nul 2>&1
echo.
echo [2/3] Préparation des ressources statiques...
python manage.py collectstatic --noinput >nul 2>&1
echo [OK] Ressources prêtes.

:: 6. Autorisation pare-feu Windows pour le port 8000
netsh advfirewall firewall show rule name="YelenSchool-SQLite-Port8000" >nul 2>&1
if %ERRORLEVEL% neq 0 (
    netsh advfirewall firewall add rule name="YelenSchool-SQLite-Port8000" dir=in action=allow protocol=TCP localport=8000 >nul 2>&1
)

:: 7. Affichage et Lancement du serveur Web multi-threads
echo.
echo =====================================================================
echo [3/3] SERVEUR YELEN SCHOOL PRÊT ET ACCESSIBLE SUR LE RÉSEAU !
echo.
echo 🖥️  Sur ce PC Serveur :           http://localhost:8000
if not "%LAN_IP%"=="" (
echo 🌐  Depuis les AUTRES PC du réseau :  http://%LAN_IP%:8000
) else (
echo 🌐  Depuis les AUTRES PC du réseau :  http://[IP_DE_CE_PC]:8000
)
echo.
echo Capacite : 15 a 25 postes clients simultanes (Caisse, Secretariat, etc.)
echo Pour arreter le serveur, fermez simplement cette fenetre.
echo =====================================================================
echo.

:: Ouvre automatiquement le navigateur sur le poste serveur
start http://localhost:8000

:: Lancement du serveur WSGI avec 8 threads concurrents si waitress est présent, sinon runserver 0.0.0.0
python -c "import waitress" >nul 2>&1
if %ERRORLEVEL% equ 0 (
    echo Demarrage avec le serveur de production multi-threads Waitress...
    python -m waitress --host=0.0.0.0 --port=8000 --threads=8 yelen_school.wsgi:application
) else (
    echo Demarrage avec Django Server (0.0.0.0:8000)...
    python manage.py runserver 0.0.0.0:8000
)

pause
