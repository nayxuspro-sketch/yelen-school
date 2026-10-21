@echo off
setlocal
cd /d "%~dp0"

rem Programme la verification des paiements Mobile Money en ligne (CinetPay) toutes les 10 minutes.
rem Exemple : programmer-verification-paiements.bat -Minutes 5

net session >nul 2>&1
if not "%ERRORLEVEL%"=="0" (
    echo.
    echo Ce script doit etre lance en tant qu'administrateur.
    echo Faites un clic droit dessus puis choisissez "Executer en tant qu'administrateur".
    pause
    exit /b 1
)

powershell.exe -NoProfile -ExecutionPolicy Bypass ^
  -File "%~dp0installer\register-mobile-money-task.ps1" %*
set "EXIT_CODE=%ERRORLEVEL%"

if "%EXIT_CODE%"=="0" (
    echo.
    echo Verification des paiements en ligne configuree.
    echo Journal : logs\paiements-en-ligne.log
) else (
    echo.
    echo Echec de la programmation de la verification des paiements.
    pause
)

exit /b %EXIT_CODE%
