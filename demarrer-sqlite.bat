@echo off
if exist "%~dp0verifier-integrite-anti-copie.bat" (
    call "%~dp0verifier-integrite-anti-copie.bat"
    if errorlevel 1 exit /b 1
)
setlocal enabledelayedexpansion
chcp 65001 >nul 2>&1
cd /d "%~dp0.."

title YELEN SCHOOL - Mode Autonome (SQLite)
color 0B

echo =====================================================================
echo           YELEN SCHOOL - MODE AUTONOME SANS DOCKER (SQLITE)
echo =====================================================================
echo.

:: 1. Vérification de Python local
where python >nul 2>&1
if %ERRORLEVEL% neq 0 (
    color 0C
    echo [ERREUR] Python n'est pas installe sur cette machine ou n'est pas dans le PATH.
    echo          Veuillez installer Python 3.10+ depuis https://www.python.org/
    echo          (Pensez a cocher "Add Python to PATH").
    pause
    exit /b 1
)
echo [OK] Python detecte.

:: 2. Configuration automatique du fichier .env pour SQLite
if not exist ".env" (
    if exist ".env.example" (
        copy /y ".env.example" ".env" >nul
        echo [INFO] Fichier .env cree depuis .env.example.
    ) else (
        type nul > ".env"
    )
)

echo [INFO] Configuration du mode SQLite dans .env...

:: Script PowerShell inline pour injecter ou mettre à jour proprement DB_ENGINE et CACHE_BACKEND
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
    "if (-not ($content -match 'SECRET_KEY=[a-zA-Z0-9]')) {" ^
    "    $rnd = [System.Guid]::NewGuid().ToString('N') + [System.Guid]::NewGuid().ToString('N');" ^
    "    Set-EnvVar 'SECRET_KEY' $rnd;" ^
    "};" ^
    "[System.IO.File]::WriteAllText($envFile, $script:content.Trim() + [Environment]::NewLine, [System.Text.Encoding]::UTF8);"

if not exist "data" mkdir "data"

echo [OK] .env configure automatiquement avec DB_ENGINE=sqlite.
echo.

:: 3. Application des migrations de base de données
echo [1/3] Application des migrations de la base SQLite...
python manage.py migrate --noinput
if %ERRORLEVEL% neq 0 (
    color 0C
    echo [ERREUR] Echec lors de la migration de la base SQLite.
    pause
    exit /b 1
)
echo [OK] Base de donnees prete dans data\yelen_school.sqlite3.

:: 4. Creation de la table de cache si necessaire
python manage.py createcachetable >nul 2>&1

:: 5. Collecte des fichiers statiques
echo.
echo [2/3] Verification des fichiers statiques...
python manage.py collectstatic --noinput >nul 2>&1
echo [OK] Fichiers statiques prets.

:: 6. Lancement du serveur Web local
echo.
echo [3/3] Demarrage du serveur YELEN SCHOOL sur http://localhost:8000 ...
echo =====================================================================
echo Application accessible a l'adresse : http://localhost:8000
echo Pour arreter l'application, fermez simplement cette fenetre.
echo =====================================================================
echo.

:: Ouvre automatiquement le navigateur
start http://localhost:8000

:: Lancement via waitress ou runserver selon disponibilite
python -c "import waitress" >nul 2>&1
if %ERRORLEVEL% equ 0 (
    python -m waitress --port=8000 --threads=8 yelen_school.wsgi:application
) else (
    python manage.py runserver 0.0.0.0:8000
)

pause
