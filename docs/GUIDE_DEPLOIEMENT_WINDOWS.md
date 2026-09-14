# Guide de déploiement Windows — YELEN SCHOOL

## Installation locale autonome chez un client

> **Public :** administrateur technique de l'établissement.
>
> **Objectif :** installer YELEN SCHOOL sur une machine Windows avec PostgreSQL et Redis gérés localement par Docker Desktop. Après l'installation initiale, l'application fonctionne sur le réseau local sans connexion Internet quotidienne.

---

## Sommaire

1. [Architecture et prérequis](#1-architecture-et-prérequis)
2. [Installation initiale](#2-installation-initiale)
3. [Configuration et premier accès](#3-configuration-et-premier-accès)
4. [Utilisation quotidienne](#4-utilisation-quotidienne)
5. [Sauvegardes PostgreSQL et médias](#5-sauvegardes-postgresql-et-médias)
6. [Programmation automatique](#6-programmation-automatique)
7. [Restauration après incident](#7-restauration-après-incident)
8. [Mise à jour sans perte de données](#8-mise-à-jour-sans-perte-de-données)
9. [Accès depuis le réseau local](#9-accès-depuis-le-réseau-local)
10. [Dépannage et vérifications](#10-dépannage-et-vérifications)
11. [Reprise sur une nouvelle machine](#11-reprise-sur-une-nouvelle-machine)

---

## 1. Architecture et prérequis

### 1.1 Ce qui est installé

La distribution client utilise le fichier `docker-compose.client.yml` :

| Service | Rôle | Persistance |
|---|---|---|
| `web` | Application Django et Gunicorn | volume médias, fichiers statiques et journaux |
| `db` | PostgreSQL 15 | volume `yelen_postgres_data` |
| `redis` | Cache et sessions | volume `yelen_redis_data` |

Les volumes Docker `yelen_postgres_data`, `yelen_redis_data`, `yelen_media`, `yelen_staticfiles` et `yelen_logs` ne doivent jamais être supprimés pendant une opération normale. La commande `docker compose down -v` efface les données et est interdite sauf si une restauration complète est prévue.

Le fichier `docker-compose.dev.yml` est réservé au développement. Pour une installation client, utiliser exclusivement `docker-compose.client.yml` et les scripts du dossier `installer`.

### 1.2 Prérequis machine

- Windows 10 64 bits récent ou Windows 11 ;
- au moins 8 Go de RAM et 20 Go d'espace libre, davantage selon le volume des médias ;
- Docker Desktop installé, démarré et configuré avec le moteur Linux ;
- accès administrateur lors de l'installation de Docker Desktop ;
- PowerShell 5.1 ou PowerShell 7 ;
- une adresse IP fixe ou réservée sur le réseau local est recommandée pour le poste serveur ;
- un support externe ou un autre poste pour copier les sauvegardes.

La première installation télécharge l'image PostgreSQL, l'image Redis et les dépendances Python. Une connexion Internet est donc nécessaire à ce moment-là. Les démarrages et l'utilisation courante sont ensuite locaux, tant que les images Docker sont déjà présentes.

### 1.3 Dossier de l'application

Choisir un dossier simple, par exemple `C:\YELEN-SCHOOL`. Le chemin peut contenir des espaces ; les scripts utilisent des chemins absolus. Ne pas placer les sauvegardes uniquement sur le même disque que l'ordinateur serveur.

---

## 2. Installation initiale

### 2.1 Obtenir les fichiers

Copier l'archive fournie par l'équipe YELEN SCHOOL dans le dossier choisi, ou cloner le dépôt avec Git :

```powershell
New-Item -ItemType Directory -Force C:\YELEN-SCHOOL | Out-Null
Set-Location C:\YELEN-SCHOOL
git clone URL_DU_DEPOT .
```

Vérifier que `docker-compose.client.yml`, `Dockerfile`, `demarrage.bat` et le dossier `installer` sont directement présents à la racine.

### 2.2 Installation recommandée

1. Démarrer Docker Desktop et attendre qu'il indique qu'il est opérationnel.
2. Ouvrir l'Explorateur dans le dossier YELEN SCHOOL.
3. Double-cliquer sur `demarrage.bat`.

Le script appelle `installer\install-windows.bat` et :

- vérifie que Docker répond ;
- crée `.env` depuis `.env.example` si nécessaire ;
- génère une clé Django et un mot de passe PostgreSQL local ;
- configure `DB_HOST=db`, Redis et les hôtes du réseau local ;
- crée ou met à jour la règle entrante Windows `YELEN SCHOOL - Accès réseau local` pour le port TCP `YELEN_HTTP_PORT`, uniquement sur les profils privé ou domaine et le sous-réseau local ;
- démarre `docker-compose.client.yml` avec `--build` ;
- applique les migrations et collecte les fichiers statiques via `entrypoint.sh` ;
- crée le compte administrateur initial lors d'une nouvelle installation ;
- ouvre la page de connexion quand le service est prêt.

Équivalent PowerShell, utile pour voir les messages ou désactiver l'ouverture du navigateur :

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass `
  -File .\installer\install-windows.ps1 -NoBrowser
```

Ne lancez pas `docker compose down -v` pour résoudre un simple problème de démarrage : cela détruirait les volumes et les données.

### 2.3 Si l'installation échoue

Afficher les journaux du service web :

```powershell
docker compose -f docker-compose.client.yml logs --tail=120 web
docker compose -f docker-compose.client.yml ps
```

Les causes habituelles sont Docker Desktop arrêté, un port `8000` déjà utilisé, ou un manque d'espace disque. Corriger la cause puis relancer `demarrage.bat`. Le démarrage est idempotent : il réutilise `.env` et les volumes existants.

---

## 3. Configuration et premier accès

### 3.1 Compte initial

Pour une nouvelle installation, le compte créé automatiquement est :

- **Email :** `admin@yelen.edu`
- **Mot de passe initial :** `admin123`

Changer ce mot de passe immédiatement après la première connexion. Le script passe ensuite `ENSURE_ADMIN` à `false` afin de ne pas réinitialiser le mot de passe aux redémarrages suivants.

### 3.2 Fichier `.env`

Le fichier `.env` contient les secrets et reste sur la machine cliente. Il est ignoré par Git et ne doit pas être envoyé avec une archive de support. Conserver une copie chiffrée ou papier des informations nécessaires à la reprise :

```dotenv
DB_NAME=yelen_school_db
DB_USER=yelen_user
DB_PASSWORD=mot_de_passe_genere_localement
DB_HOST=db
DB_PORT=5432
REDIS_URL=redis://redis:6379/0
```

Ne pas remplacer `DB_PASSWORD` sur une installation existante sans procédure de migration : PostgreSQL a été initialisé avec ce mot de passe. Les scripts d'installation ne réécrivent pas une valeur existante valide.

Les sauvegardes `.dump` et `_media.tar.gz` ne contiennent pas `.env`. Sauvegarder donc `.env` séparément, dans un emplacement protégé, si une reprise complète est prévue.

### 3.3 Adresse locale

Sur le serveur : `http://localhost:8000/accounts/login/`.

Depuis un autre poste du réseau, utiliser l'adresse IP du serveur, par exemple `http://192.168.1.50:8000/`. Le script d'installation ajoute l'IP détectée aux hôtes autorisés. Si l'adresse IP change, relancer l'installation ou mettre à jour `.env`, puis reconstruire le service web.

---

## 4. Utilisation quotidienne

### 4.1 Démarrer, arrêter et vérifier

```powershell
# Démarrer ou remettre les trois services en arrière-plan
docker compose -f docker-compose.client.yml up -d

# Vérifier l'état et les healthchecks
docker compose -f docker-compose.client.yml ps

# Afficher les journaux de l'application
docker compose -f docker-compose.client.yml logs -f web

# Arrêter les services sans supprimer les volumes
docker compose -f docker-compose.client.yml down
```

L'arrêt normal ne supprime ni PostgreSQL, ni Redis, ni les médias. Pour une utilisation quotidienne, il suffit généralement de laisser Docker Desktop et les services fonctionner.

### 4.2 Démarrage automatique avec Windows

Pour que YELEN SCHOOL démarre automatiquement après l'ouverture de session Windows :

1. Démarrer Docker Desktop et effectuer une première installation avec `demarrage.bat`.
2. Depuis la racine du projet, faire un clic droit sur `programmer-demarrage.bat`.
3. Choisir **Exécuter en tant qu'administrateur**.
4. Vérifier la création de la tâche `YELEN SCHOOL - Démarrage automatique`.

À chaque ouverture de session, la tâche attend que Docker Desktop réponde puis exécute `docker compose -f docker-compose.client.yml up -d`. Elle ne reconstruit pas l'image et ne supprime aucun volume. Le journal est écrit dans `logs\startup.log`.

Cette tâche s'exécute dans la session de l'utilisateur qui l'a enregistrée. Configurer Docker Desktop pour démarrer avec Windows. Tester le fonctionnement en redémarrant Windows, puis vérifier :

```powershell
docker compose -f docker-compose.client.yml ps
```

En cas de changement de code ou de dépendances, utiliser `demarrage.bat` pour reconstruire l'image avec `--build`. Le démarrage automatique quotidien reste volontairement plus rapide et local, sans reconstruction.

### 4.3 Avant d'éteindre le serveur

1. Vérifier qu'aucune restauration ou mise à jour n'est en cours.
2. Vérifier que la sauvegarde quotidienne précédente est présente.
3. Arrêter Windows normalement ; ne pas supprimer les volumes Docker.

---

## 5. Sauvegardes PostgreSQL et médias

### 5.1 Sauvegarde manuelle

Depuis le dossier racine du projet :

```powershell
installer\backup-windows.bat
```

Ou directement :

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass `
  -File .\installer\backup-windows.ps1
```

Le script sauvegarde PostgreSQL et le volume Docker `yelen_media` en deux fichiers associés dans `backups\` :

```text
backups\yelen_school_YYYYMMDD_HHMMSS.dump
backups\yelen_school_YYYYMMDD_HHMMSS_media.tar.gz
```

Le fichier `.dump` est un dump PostgreSQL au format custom. L'archive `_media.tar.gz` contient les fichiers téléversés dans `/app/media`. Les deux fichiers constituent une seule sauvegarde : les copier et les conserver ensemble.

Un fichier temporaire `.part` est utilisé pendant chaque export. En cas d'échec, le script supprime les fichiers incomplets et ne laisse pas croire qu'une sauvegarde est valide.

### 5.2 Rétention et copie hors machine

Par défaut, les 30 paires les plus récentes sont conservées. Pour modifier la rétention :

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass `
  -File .\installer\backup-windows.ps1 -Keep 60
```

La rétention locale ne remplace pas une copie externe. Après la sauvegarde, copier au minimum la paire la plus récente vers un disque USB, un NAS ou un autre ordinateur. Vérifier que les deux noms ont exactement le même horodatage.

Ne pas inclure `.env` dans une copie non chiffrée. Si `.env` est copié pour la reprise, le protéger comme un mot de passe.

### 5.3 Vérification d'une sauvegarde

Vérifier la présence et la taille des deux fichiers :

```powershell
Get-ChildItem .\backups\yelen_school_*.dump, .\backups\yelen_school_*_media.tar.gz |
  Sort-Object LastWriteTime -Descending |
  Select-Object -First 4 Name, Length, LastWriteTime
```

La vérification complète consiste à restaurer la paire sur une installation de test, au moins une fois par trimestre. Ne pas tester une restauration destructive sur la machine de production sans sauvegarde récente supplémentaire.

---

## 6. Programmation automatique

### 6.1 Tâche planifiée Windows

Depuis le dossier racine, faire un clic droit sur `programmer-sauvegarde.bat`, puis choisir **Exécuter en tant qu'administrateur**.

Le script programme la sauvegarde tous les jours à 22 h par défaut. Pour choisir une autre heure depuis PowerShell :

```powershell
.\programmer-sauvegarde.bat 23:30
```

Le script technique équivalent reste disponible ici :

```powershell
.\installer\register-backup-task.ps1 -Time 22:00
```

Une tâche nommée `YELEN SCHOOL - Sauvegarde PostgreSQL et médias` est créée ou remplacée. L'heure est exprimée en format 24 heures :

```powershell
.\installer\register-backup-task.ps1 -Time 23:30
```

Dans le Planificateur de tâches, cliquer sur **Exécuter** pour effectuer un premier test. Vérifier ensuite l'apparition d'une paire de fichiers dans `backups\`.

La tâche nécessite que Docker Desktop et son moteur soient disponibles à l'heure prévue. Pour une exécution fiable, configurer Docker Desktop pour démarrer avec Windows et laisser la session qui l'exécute autorisée à utiliser Docker. Les erreurs éventuelles sont visibles dans l'historique du Planificateur et dans les journaux Docker.

### 6.2 Journal de programmation

Les sorties de la tâche sont écrites dans `backups\backup.log` si la tâche est lancée par le script fourni. Surveiller régulièrement :

- la date de modification de la dernière paire ;
- la taille du dump et de l'archive médias ;
- l'espace libre du disque ;
- la présence d'une copie hors machine.

---

## 7. Restauration après incident

> **Attention :** la restauration remplace la base PostgreSQL et, si l'archive est présente, tous les médias actuels. Elle nécessite une confirmation `RESTAURER` sauf avec l'option explicite `-Yes`.

### 7.1 Préparer la paire

Placer dans un même dossier :

```text
yelen_school_20260914_220000.dump
yelen_school_20260914_220000_media.tar.gz
```

Le nom de l'archive médias doit être obtenu en ajoutant `_media.tar.gz` au nom du dump sans son suffixe `.dump`. Si l'archive médias est absente, la base sera restaurée mais les fichiers téléversés ne le seront pas ; le script affiche un avertissement.

### 7.2 Restaurer sous Windows

Depuis la racine du projet :

```powershell
installer\restore-windows.bat .\backups\yelen_school_20260914_220000.dump
```

Ou :

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass `
  -File .\installer\restore-windows.ps1 `
  -BackupFile .\backups\yelen_school_20260914_220000.dump
```

Le script :

1. arrête le service web pour empêcher les écritures pendant la reconstruction ;
2. recrée la base PostgreSQL et importe le dump ;
3. redémarre le service web ;
4. restaure l'archive médias associée lorsqu'elle existe ;
5. garantit une tentative de redémarrage du service web même en cas d'erreur.

Pour une exécution non interactive dans une procédure déjà validée :

```powershell
.\installer\restore-windows.ps1 `
  -BackupFile .\backups\yelen_school_20260914_220000.dump -Yes
```

N'utiliser `-Yes` qu'après avoir vérifié le chemin de la sauvegarde. Après restauration, se connecter, contrôler quelques élèves, paiements et documents, puis vérifier quelques fichiers médias.

### 7.3 Programmer une restauration unique sous Windows

Une restauration automatique est destructive. Le script fourni programme donc une seule exécution, et non une restauration quotidienne. Vérifier la paire, prévenir les utilisateurs et s'assurer que Docker Desktop sera disponible à l'heure choisie.

Depuis la racine du projet, faire un clic droit sur `programmer-restauration.bat`, puis choisir **Exécuter en tant qu'administrateur**. Depuis un terminal administrateur :

```powershell
.\programmer-restauration.bat `
  ".\backups\yelen_school_20260914_220000.dump" 03:00 CONFIRMER
```

Le fichier `_media.tar.gz` associé doit être présent. Le mot `CONFIRMER` est obligatoire pour éviter une programmation accidentelle. La tâche est visible dans le Planificateur de tâches sous `YELEN SCHOOL - Restauration programmée` et son journal est écrit dans `backups\restore.log`.

Avant l'heure prévue, il est possible d'annuler la tâche depuis le Planificateur de tâches. Ne programmez pas cette opération pendant l'utilisation de l'application.

### 7.4 Restauration depuis Linux/macOS

La même paire peut être restaurée avec :

```bash
./installer/restore-local.sh backups/yelen_school_20260914_220000.dump
```

Cette commande est documentée ici pour les installations multiplateformes ; elle utilise également `docker-compose.client.yml` et PostgreSQL local.

### 7.5 Si la restauration échoue

Ne pas supprimer les volumes et ne pas relancer une restauration avec une paire incomplète. Conserver le dump original, noter le message affiché, puis consulter :

```powershell
docker compose -f docker-compose.client.yml ps
docker compose -f docker-compose.client.yml logs --tail=150 db web
```

Si la base a été recréée mais que l'import a échoué, relancer la restauration avec une autre paire valide. Le service web est remis en route automatiquement, mais l'application ne doit être déclarée opérationnelle qu'après vérification de la base.

---

## 8. Mise à jour sans perte de données

### 8.1 Avant de remplacer le code

1. Prévenir les utilisateurs.
2. Exécuter une sauvegarde complète avec `installer\backup-windows.bat`.
3. Vérifier la paire `.dump` et `_media.tar.gz`.
4. Copier cette paire hors de la machine.
5. Conserver `.env` séparément.

### 8.2 Mise à jour avec Git

```powershell
Set-Location C:\YELEN-SCHOOL
git pull origin main
```

Si l'équipe fournit une autre branche ou une archive, suivre ses notes de version. Ne jamais remplacer `.env` par `.env.example` pendant une mise à jour.

### 8.3 Reconstruire sans effacer les volumes

```powershell
docker compose -f docker-compose.client.yml up -d --build
```

`entrypoint.sh` applique les migrations et collecte les fichiers statiques au démarrage. Vérifier ensuite :

```powershell
docker compose -f docker-compose.client.yml ps
docker compose -f docker-compose.client.yml logs --tail=100 web
```

Ne pas utiliser `docker compose down -v`, `docker volume prune` ou la suppression manuelle de `yelen_postgres_data` et `yelen_media`. Ces commandes peuvent supprimer définitivement les données.

### 8.4 Retour arrière

Si la nouvelle version ne démarre pas :

1. arrêter les utilisateurs ;
2. consulter les journaux ;
3. remettre le code de la version précédente ;
4. relancer `docker compose -f docker-compose.client.yml up -d --build` ;
5. restaurer la paire créée avant la mise à jour uniquement si les migrations ont rendu la base incompatible et si les notes de version le recommandent.

Une sauvegarde est indispensable avant toute migration de schéma.

---

## 9. Accès depuis le réseau local

### 9.1 Adresse à communiquer

Depuis un poste client, ouvrir :

```text
http://ADRESSE_IP_DU_SERVEUR:8000/
```

Pour connaître l'adresse IPv4 du serveur :

```powershell
Get-NetIPAddress -AddressFamily IPv4 |
  Where-Object {$_.IPAddress -notlike '127.*' -and $_.IPAddress -notlike '169.254.*'}
```

### 9.2 Pare-feu Windows

Lors de chaque exécution de `demarrage.bat`, le script crée ou met à jour automatiquement la règle :

```text
YELEN SCHOOL - Accès réseau local
```

La règle autorise uniquement le port TCP défini par `YELEN_HTTP_PORT` (8000 par défaut), sur les profils réseau **Privé** ou **Domaine** et depuis le sous-réseau local. Elle ne s'applique pas au profil Public. Si Windows affiche une demande UAC, l'accepter pour permettre l'accès depuis les autres postes. Si elle est refusée, l'application reste accessible sur le serveur mais peut rester inaccessible depuis le réseau local.

En cas de changement de port, relancer `demarrage.bat` : l'ancienne règle YELEN SCHOOL est remplacée par la règle correspondant au nouveau port.

Pour vérifier la règle depuis PowerShell administrateur :

```powershell
Get-NetFirewallRule -Name YELEN_SCHOOL_LocalWeb |
  Get-NetFirewallPortFilter
```

Pour la supprimer manuellement si nécessaire :

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass `
  -File .\installer\configure-firewall.ps1 -Port 8000 -Remove
```

Ne pas exposer directement PostgreSQL (`5432`) ou Redis (`6379`) au réseau : ces services restent internes à Docker. Le navigateur des utilisateurs n'a pas besoin d'Internet pour accéder à l'application ; il doit seulement atteindre le serveur sur le réseau local.

---

## 10. Dépannage et vérifications

### Docker Desktop ne répond pas

- ouvrir Docker Desktop et attendre son état opérationnel ;
- vérifier `docker info` ;
- vérifier que le moteur Linux est sélectionné ;
- relancer `demarrage.bat`.

### Les services ne sont pas prêts

```powershell
docker compose -f docker-compose.client.yml ps
docker compose -f docker-compose.client.yml logs --tail=200 db
docker compose -f docker-compose.client.yml logs --tail=200 web
```

PostgreSQL doit être `healthy` avant que le service web soit disponible. La première construction peut être longue.

### Le port 8000 est déjà utilisé

Modifier `YELEN_HTTP_PORT` dans `.env`, par exemple :

```dotenv
YELEN_HTTP_PORT=8001
```

Puis relancer :

```powershell
docker compose -f docker-compose.client.yml up -d --build
```

L'adresse devient `http://localhost:8001/`. Relancer `demarrage.bat` afin que la règle du pare-feu soit automatiquement remplacée, puis mettre à jour l'adresse communiquée aux postes clients.

### L'application affiche une erreur de connexion PostgreSQL

Vérifier que `DB_NAME`, `DB_USER` et `DB_PASSWORD` sont cohérents avec le fichier `.env` utilisé lors de l'initialisation. Ne pas changer le mot de passe au hasard sur une base existante. Vérifier l'état :

```powershell
docker compose -f docker-compose.client.yml exec db pg_isready `
  -U yelen_user -d yelen_school_db
```

### Les médias ont disparu après un incident

Ne pas supprimer `yelen_media`. Rechercher la paire de sauvegarde correspondante et exécuter la restauration complète avec le dump `.dump`. L'archive `_media.tar.gz` est restaurée automatiquement par `restore-windows.ps1`.

### La tâche planifiée n'a rien produit

- vérifier l'historique de la tâche ;
- vérifier que Docker Desktop est démarré à l'heure prévue ;
- exécuter manuellement `installer\backup-windows.bat` ;
- vérifier les droits d'accès au dossier `backups\` ;
- vérifier l'espace disque et les journaux Docker.

---

## 11. Reprise sur une nouvelle machine

1. Installer Windows et Docker Desktop.
2. Copier la distribution YELEN SCHOOL dans un dossier local.
3. Restaurer le fichier `.env` sauvegardé, si disponible. À défaut, exécuter une installation neuve pour générer une configuration locale.
4. Démarrer `demarrage.bat` et attendre que PostgreSQL soit prêt.
5. Copier une paire `.dump` et `_media.tar.gz` dans `backups\`.
6. Exécuter `installer\restore-windows.bat` avec le dump.
7. Vérifier les données, les médias, le compte administrateur et l'accès réseau.
8. Reprogrammer la tâche avec `installer\register-backup-task.bat`.
9. Copier une nouvelle sauvegarde vers un support externe.

Si le fichier `.env` original est restauré, les secrets Django et le mot de passe PostgreSQL restent cohérents. Si un nouveau `.env` a été généré, conserver la nouvelle configuration et vérifier l'accès après la restauration ; ne jamais mélanger un ancien volume avec des identifiants inconnus.

---

## Règles essentielles à retenir

- Utiliser `docker-compose.client.yml`, jamais le compose de développement pour le poste client.
- Utiliser les scripts fournis pour sauvegarder PostgreSQL **et** les médias.
- Conserver ensemble les fichiers `.dump` et `_media.tar.gz`.
- Copier les sauvegardes hors de la machine.
- Ne jamais supprimer les volumes Docker pour résoudre un problème courant.
- Tester une restauration périodiquement.
- Changer le mot de passe administrateur initial dès la première connexion.
- Protéger `.env` comme un secret.
