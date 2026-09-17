@echo off
chcp 65001 >nul
title YELEN SCHOOL - Déverrouillage Dossier Sécurisé (Éditeur)
color 0E

echo =====================================================================
echo       YELEN SCHOOL - OUTIL ÉDITEUR : DÉVERROUILLAGE DU DOSSIER
echo                  CONFIDENTIEL - USAGE ÉDITEUR SEUL
echo =====================================================================
echo.

:: 1. Vérification des privilèges Administrateur obligatoire
net session >nul 2>&1
if %errorlevel% neq 0 (
    color 0C
    echo [ERREUR] Ce script doit impérativement être exécuté en tant qu'Administrateur !
    echo Clic droit sur ce fichier ^-^> "Exécuter en tant qu'administrateur".
    echo.
    pause
    exit /b 1
)

:: 2. Emplacement du dossier Yelen School
set "APP_DIR=C:\YelenSchool"
if not exist "%APP_DIR%" (
    set "APP_DIR=%~dp0..\..\yelen-school"
)
if not exist "%APP_DIR%" (
    set "APP_DIR=%~dp0.."
)

echo Dossier cible detecte : %APP_DIR%
echo.
set /p "CONFIRM_PATH=Confirmez-vous ce dossier ? (O pour Valider, ou saisissez le chemin complet) : "
if /i not "%CONFIRM_PATH%"=="O" (
    if exist "%CONFIRM_PATH%" (
        set "APP_DIR=%CONFIRM_PATH%"
    )
)

if not exist "%APP_DIR%" (
    color 0C
    echo [ERREUR] Le dossier "%APP_DIR%" est introuvable.
    pause
    exit /b 1
)

echo.
echo =====================================================================
echo       AUTHENTIFICATION EDITEUR REQUISE
echo =====================================================================
:: Demande d'un code maître de maintenance (modifiable par l'éditeur)
set /p "MASTER_KEY=Entrez le Passcode Maître Editeur : "

:: Hash simple ou contrôle secret (par défaut, clé éditeur: YelenMaster2026!)
if not "%MASTER_KEY%"=="YelenMaster2026!" (
    color 0C
    echo.
    echo [ACCÈS REFUSÉ] Code maître invalide. Tentative de déverrouillage rejetée.
    pause
    exit /b 1
)

echo.
color 0A
echo [AUTHENTIFICATION REUSSIE]
echo.
echo Déverrouillage des permissions NTFS en cours...
echo.

:: Réappropriation de la propriété (Ownership) au profit du compte Administrateur en cours
echo [1/3] Récupération de la propriété du dossier...
takeown /F "%APP_DIR%" /R /D O >nul 2>&1

:: Réactivation de l'héritage et attribution du contrôle total aux Administrateurs et Utilisateurs
echo [2/3] Restauration des autorisations d'écriture et de lecture...
icacls "%APP_DIR%" /reset /T /C /Q >nul 2>&1
icacls "%APP_DIR%" /grant *S-1-5-32-544:(OI)(CI)F /T /C /Q >nul 2>&1
icacls "%APP_DIR%" /grant *S-1-5-32-545:(OI)(CI)M /T /C /Q >nul 2>&1

:: Retrait éventuel de l'attribut lecture seule / masquage
echo [3/3] Réinitialisation des attributs fichiers...
attrib -r -s -h "%APP_DIR%\*.*" /s /d >nul 2>&1

echo.
echo =====================================================================
echo [SUCCÈS] DOSSIER DÉVERROUILLÉ AVEC SUCCÈS !
echo.
echo Vous disposez maintenant d'un contrôle total (Lecture / Écriture / Modification)
echo sur l'ensemble de l'application dans :
echo %APP_DIR%
echo.
echo RAPPEL : Une fois vos opérations de maintenance terminées,
echo relancez 'verrouiller-dossier-anti-copie.bat' pour réappliquer la protection.
echo =====================================================================
echo.
pause
