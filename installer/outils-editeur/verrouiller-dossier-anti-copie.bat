@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion

echo ================================================================
echo   YELEN SCHOOL — VERROUILLAGE DES PERMISSIONS DOSSIER (ANTI-COPIE)
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

:: 2. Détection du dossier à verrouiller (par défaut C:\YELEN-SCHOOL)
set "TARGET_DIR=C:\YELEN-SCHOOL"
if not exist "%TARGET_DIR%\.env" (
    set "PARENT_DIR=%~dp0.."
    pushd "!PARENT_DIR!"
    if exist ".env" set "TARGET_DIR=!CD!"
    popd
)

if not exist "%TARGET_DIR%" (
    echo [ERREUR] Dossier introuvable : %TARGET_DIR%
    pause
    exit /b 1
)

echo Dossier cible : %TARGET_DIR%
echo.

echo [1/3] Suppression de l'héritage des permissions Windows (NTFS)...
icacls "%TARGET_DIR%" /inheritance:d >nul 2>&1

echo [2/3] Blocage des utilisateurs réguliers et invités...
:: Suppression des accès pour les groupes non privilégiés
icacls "%TARGET_DIR%" /remove "Utilisateurs" >nul 2>&1
icacls "%TARGET_DIR%" /remove "Users" >nul 2>&1
icacls "%TARGET_DIR%" /remove "Tout le monde" >nul 2>&1
icacls "%TARGET_DIR%" /remove "Everyone" >nul 2>&1
icacls "%TARGET_DIR%" /remove "Invités" >nul 2>&1
icacls "%TARGET_DIR%" /remove "Guests" >nul 2>&1

:: Accorder le contrôle total EXCLUSIVEMENT aux Administrateurs et au Système Windows
icacls "%TARGET_DIR%" /grant:r "Administrateurs":(OI)(CI)F >nul 2>&1
icacls "%TARGET_DIR%" /grant:r "Administrators":(OI)(CI)F >nul 2>&1
icacls "%TARGET_DIR%" /grant:r "SYSTEM":(OI)(CI)F >nul 2>&1

echo [3/3] Verrouillage et masquage du fichier sensible .env...
if exist "%TARGET_DIR%\.env" (
    attrib +h +s "%TARGET_DIR%\.env"
    icacls "%TARGET_DIR%\.env" /inheritance:r >nul 2>&1
    icacls "%TARGET_DIR%\.env" /grant:r "Administrateurs":F "Administrators":F "SYSTEM":F >nul 2>&1
)

echo.
echo ================================================================
echo   ✅ Le dossier est désormais STRICTEMENT PROTÉGÉ.
echo   Un utilisateur ordinaire ou une clé USB branchée sans compte
echo   Administrateur ne pourra ni lire, ni ouvrir, ni copier les fichiers.
echo.
echo   ⚠️ RAPPEL DE SÉCURITÉ :
echo   Supprimez ce fichier .bat de la machine client avant de partir.
echo ================================================================
echo.
pause
