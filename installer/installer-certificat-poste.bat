@echo off
setlocal
rem Installe l'autorite locale YELEN SCHOOL sur ce poste pour que le navigateur
rem accepte https://<serveur>:8443 sans avertissement. A executer UNE FOIS par poste,
rem en tant qu'administrateur, avec le fichier yelen-ca.crt place a cote de ce script.

net session >nul 2>&1
if not "%ERRORLEVEL%"=="0" (
    echo.
    echo Ce script doit etre lance en tant qu'administrateur.
    echo Faites un clic droit dessus puis choisissez "Executer en tant qu'administrateur".
    pause
    exit /b 1
)

set "CA=%~dp0yelen-ca.crt"
if not exist "%CA%" set "CA=%~dp0..\certs\yelen-ca.crt"
if not exist "%CA%" (
    echo.
    echo Fichier yelen-ca.crt introuvable a cote de ce script.
    echo Copiez-le depuis le serveur : C:\YELEN-SCHOOL\certs\yelen-ca.crt
    pause
    exit /b 1
)

certutil -addstore -f Root "%CA%"
if not "%ERRORLEVEL%"=="0" (
    echo.
    echo Echec de l'installation du certificat.
    pause
    exit /b 1
)

echo.
echo Autorite YELEN SCHOOL installee. Fermez puis rouvrez le navigateur.
echo Firefox : si un avertissement persiste, Parametres ^> Vie privee et securite ^> Certificats ^> Importer yelen-ca.crt.
pause
exit /b 0
