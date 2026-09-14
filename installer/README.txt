YELEN SCHOOL — INSTALLATION LOCALE

Windows
-------
Double-cliquer sur install-windows.bat.
Le script vérifie Docker Desktop, prépare .env, construit l'image et démarre
PostgreSQL, Redis et l'application.

Commande PowerShell équivalente :
  powershell -ExecutionPolicy Bypass -File .\installer\install-windows.ps1

Linux / macOS
=============
  chmod +x installer/install-local.sh
  ./installer/install-local.sh

Après l'installation
====================
  Adresse locale : http://localhost:8000/accounts/login/
  Compte initial : admin@yelen.edu
  Mot de passe   : admin123

Changez le mot de passe dès la première connexion.

Les données PostgreSQL, Redis, les médias, les fichiers statiques et les logs
sont conservés dans des volumes Docker nommés. Ne supprimez pas ces volumes
sans disposer d'une sauvegarde.

Commandes utiles
================
  docker compose -f docker-compose.client.yml ps
  docker compose -f docker-compose.client.yml logs -f web
  docker compose -f docker-compose.client.yml down
  docker compose -f docker-compose.client.yml up -d
