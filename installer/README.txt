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
  Mot de passe   : généré aléatoirement et affiché une seule fois par l'installateur

Le changement du mot de passe est obligatoire à la première connexion. Le secret
temporaire est retiré de `.env` après le démarrage réussi.

Accès réseau local et pare-feu Windows
--------------------------------------
Lors de la première exécution de demarrage.bat, ou lorsqu'un changement de
port le rend nécessaire, le script crée ou met à jour la règle Windows
« YELEN SCHOOL - Accès réseau local » pour le port défini par YELEN_HTTP_PORT
(8000 par défaut). La règle autorise uniquement le trafic TCP sur les profils
réseau privé ou domaine et le sous-réseau local. Elle ne s'applique pas au
profil Public. La tâche de démarrage automatique réutilise la règle conforme
sans demander une élévation UAC à chaque ouverture de session.

Accepter la demande UAC lors de la création ou de la modification de la règle
pour que les autres postes puissent accéder à l'application. L'application
reste accessible sur le serveur si la demande UAC est refusée, mais l'accès
depuis le réseau local peut être bloqué par le pare-feu.

Lors d'une nouvelle installation, un secret `SMS_WEBHOOK_TOKEN` est généré
pour protéger le webhook SMS. Ne pas le remplacer par une valeur publique et
ne pas partager le fichier `.env`.

Si le port demandé est occupé, demarrage.bat essaie automatiquement les ports
8000, 8001, 8002, 8003, 8004 puis 8005. Le port sélectionné est conservé dans
.env et affiché à la fin de l'installation. Si toute la plage est occupée,
définir un autre YELEN_HTTP_PORT libre dans .env puis relancer le script.

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

Analyse automatique du risque de décrochage — Windows
-----------------------------------------------------
Pour recalculer chaque nuit les scores de risque des élèves :
  Depuis la racine, clic droit sur programmer-risques.bat
  puis « Exécuter en tant qu'administrateur ».

L'heure par défaut est 02:00. Pour choisir une autre heure :
  programmer-risques.bat 03:30

La tâche « YELEN SCHOOL - Analyse du risque de décrochage » exécute la commande
Django dans le conteneur web sans reconstruire l'image. Son journal est dans
logs\risques.log. Tester la tâche depuis le Planificateur de tâches Windows.
Docker Desktop doit être démarré et le serveur doit avoir une année scolaire
courante configurée.

SMS automatiques — Windows
---------------------------
Pour exécuter chaque matin les déclencheurs SMS actifs :
  Depuis la racine, clic droit sur programmer-sms.bat
  puis « Exécuter en tant qu'administrateur ».

L'heure par défaut est 07:00. Pour choisir une autre heure :
  programmer-sms.bat 08:00

La tâche « YELEN SCHOOL - SMS automatiques » exécute `sms_auto` dans le
conteneur web et écrit son journal dans logs\sms-auto.log. Les SMS doivent être
activés et la passerelle locale configurée. Chaque déclencheur est protégé
contre une seconde exécution le même jour.

Démarrage automatique de l'application — Windows
------------------------------------------------
Pour démarrer YELEN SCHOOL automatiquement à chaque ouverture de session :
  Depuis la racine, clic droit sur programmer-demarrage.bat
  puis « Exécuter en tant qu'administrateur ».

La tâche « YELEN SCHOOL - Démarrage automatique » attend que Docker Desktop
réponde, vérifie le port conservé dans .env, puis exécute docker compose up -d.
Si le port est occupé par un autre programme, elle essaie automatiquement les
ports 8000 à 8005, conserve le nouveau port dans .env et actualise le pare-feu.
Elle ne reconstruit pas l'image et ne supprime aucun volume. Son journal est
dans logs\startup.log. Si le pare-feu ne peut pas être actualisé, relancer
demarrage.bat et accepter la demande UAC.

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
confirmation explicite est demandée, sauf si l'option --yes est fournie. Les
scripts terminent par `manage.py check` puis vérifient `/health/` (PostgreSQL et
Redis) ; contrôler ensuite manuellement un élève, un paiement, un PDF et un
fichier média.

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
