@echo off
setlocal
cd /d "%~dp0"

rem Programme l'analyse quotidienne du risque de decrochage.
rem Heure par defaut : 02:00. Exemple : programmer-risques.bat 03:30

net session >nul 2>&1
if not "%ERRORLEVEL%"=="0" (
    echo.
    echo Ce script doit etre lance en tant qu'administrateur.
    echo Faites un clic droit dessus puis choisissez "Executer en tant qu'administrateur".
    pause
    exit /b 1
)

powershell.exe -NoProfile -ExecutionPolicy Bypass ^
  -File "%~dp0installer\register-risk-task.ps1" %*
set "EXIT_CODE=%ERRORLEVEL%"

if "%EXIT_CODE%"=="0" (
    echo.
    echo Analyse quotidienne du risque configuree.
    echo Testez-la depuis le Planificateur de taches Windows.
) else (
    echo.
    echo Echec de la programmation de l'analyse du risque.
    pause
)

exit /b %EXIT_CODE%
