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

Sauvegarde PostgreSQL et médias
-------------------------------
Windows :
  Double-cliquer sur backup-windows.bat
  ou : powershell -ExecutionPolicy Bypass -File .\installer\backup-windows.ps1

Linux / macOS :
  ./installer/backup-local.sh

Chaque sauvegarde produit deux fichiers associés dans backups/ :
  yelen_school_YYYYMMDD_HHMMSS.dump
  yelen_school_YYYYMMDD_HHMMSS_media.tar.gz

Les 30 sauvegardes les plus récentes sont conservées par défaut. Ce dossier
est ignoré par Git.

Programmation automatique
-------------------------
Windows, tous les jours à 22 h :
  Depuis la racine, clic droit sur programmer-sauvegarde.bat
  puis « Exécuter en tant qu'administrateur ».
  Pour une autre heure : programmer-sauvegarde.bat 23:30
  Script technique : powershell -ExecutionPolicy Bypass -File .\installer\register-backup-task.ps1
  Journal : backups\backup.log
  La tâche s'exécute dans la session Windows qui l'enregistre ; Docker Desktop
  doit être configuré pour démarrer avec Windows.

Linux / macOS, tous les jours à 22 h :
  ./installer/register-backup-cron.sh 22:00

Restauration PostgreSQL et médias
---------------------------------
Windows :
  installer\restore-windows.bat backups\yelen_school_YYYYMMDD_HHMMSS.dump

Linux / macOS :
  ./installer/restore-local.sh backups/yelen_school_YYYYMMDD_HHMMSS.dump

L'archive des médias associée (_media.tar.gz) est restaurée automatiquement si
elle est présente. La restauration remplace toutes les données actuelles. Une
confirmation explicite est demandée, sauf si l'option --yes est fournie.

Restauration programmée — Windows
---------------------------------
Cette opération est destructive et est donc programmée une seule fois, jamais
quotidiennement par défaut. Utiliser uniquement après avoir vérifié la paire de
sauvegarde et l'absence d'utilisateurs connectés :
  programmer-restauration.bat "backups\yelen_school_YYYYMMDD_HHMMSS.dump" 03:00 CONFIRMER

Le fichier associé _media.tar.gz doit être présent. La tâche écrit son journal
dans backups\restore.log et peut être vérifiée dans le Planificateur de tâches.

Commandes utiles
----------------
  docker compose -f docker-compose.client.yml ps
  docker compose -f docker-compose.client.yml logs -f web
  docker compose -f docker-compose.client.yml down
  docker compose -f docker-compose.client.yml up -d
