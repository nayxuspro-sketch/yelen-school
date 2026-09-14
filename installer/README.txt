YELEN SCHOOL — INSTALLATION LOCALE

Windows
-------
Double-cliquer sur install-windows.bat.
Le script vérifie Docker Desktop, prépare .env, construit l'image et démarre
PostgreSQL, Redis et l'application.

Commande PowerShell équivalente :
  powershell -ExecutionPolicy Bypass -File .\installer\install-windows.ps1

Linux / macOS
-------------
  chmod +x installer/install-local.sh
  ./installer/install-local.sh

Après l'installation
--------------------
  Adresse locale : http://localhost:8000/accounts/login/
  Compte initial : admin@yelen.edu
  Mot de passe   : admin123

Changez le mot de passe dès la première connexion.

Les données PostgreSQL, Redis, les médias, les fichiers statiques et les logs
sont conservés dans des volumes Docker nommés. Ne supprimez pas ces volumes
sans disposer d'une sauvegarde.

Sauvegarde PostgreSQL
---------------------
Windows :
  Double-cliquer sur backup-windows.bat
  ou : powershell -ExecutionPolicy Bypass -File .\installer\backup-windows.ps1

Linux / macOS :
  ./installer/backup-local.sh

Les sauvegardes sont créées dans backups/ et les 30 plus récentes sont
conservées par défaut. Ce dossier est ignoré par Git.

Restauration PostgreSQL
-----------------------
Windows :
  installer\restore-windows.bat backups\yelen_school_YYYYMMDD_HHMMSS.dump

Linux / macOS :
  ./installer/restore-local.sh backups/yelen_school_YYYYMMDD_HHMMSS.dump

La restauration remplace toutes les données actuelles. Une confirmation
explicite est demandée, sauf si l'option --yes est fournie.

Commandes utiles
----------------
  docker compose -f docker-compose.client.yml ps
  docker compose -f docker-compose.client.yml logs -f web
  docker compose -f docker-compose.client.yml down
  docker compose -f docker-compose.client.yml up -d
