# Guide de Déploiement — YELEN SCHOOL
### Installation sur machine Windows — Déploiement local/on-premise

> **Document destiné à :** l'administrateur technique de l'établissement qui installe et maintient YELEN SCHOOL.
> **Niveau requis :** savoir utiliser l'Explorateur Windows, taper des commandes dans un terminal (cmd ou PowerShell).
> **Si vous bloquez :** chaque section contient une ligne "Si ça ne marche pas" avec la solution immédiate.

---

## SOMMAIRE

1. [Prérequis — Ce qu'il faut avant de commencer](#1-prérequis--ce-quil-faut-avant-de-commencer)
2. [Préparation de la machine — Installation des outils](#2-préparation-de-la-machine--installation-des-outils)
3. [Installation pas à pas — Mise en place de l'application](#3-installation-pas-à-pas--mise-en-place-de-lapplication)
4. [Configuration des fichiers sensibles (.env)](#4-configuration-des-fichiers-sensibles-env)
5. [Premier démarrage et vérification](#5-premier-démarrage-et-vérification)
6. [Procédure de vérification post-déploiement](#6-procédure-de-vérification-post-déploiement)
7. [Utilisation au quotidien — Lancer et arrêter l'application](#7-utilisation-au-quotidien--lancer-et-arrêter-lapplication)
8. [Sauvegarde et restauration de la base de données](#8-sauvegarde-et-restauration-de-la-base-de-données)
9. [Procédure de mise à jour — Nouvelle version](#9-procédure-de-mise-à-jour--nouvelle-version)
10. [Accès depuis les autres postes du réseau](#10-accès-depuis-les-autres-postes-du-réseau)
11. [Erreurs fréquentes et résolution (Troubleshooting)](#11-erreurs-fréquentes-et-résolution-troubleshooting)
12. [Annexes](#12-annexes)

---

## 1. Prérequis — Ce qu'il faut avant de commencer

### 1.1 Configuration minimale de la machine serveur

La machine qui fera office de serveur doit rester allumée pendant les heures d'utilisation (tout le personnel y accède via le réseau local). Choisissez-la en conséquence — de préférence un PC fixe, pas un portable qui sera emporté le soir.

| Composant | Minimum | Recommandé |
|-----------|---------|------------|
| Système | Windows 10 64-bit (21H2+) ou Windows 11 | Windows 11 Pro |
| Processeur | 4 cœurs, 2.0 GHz | Intel i5 / AMD Ryzen 5 ou supérieur |
| RAM | 8 Go | 16 Go (pour 300+ élèves) |
| Disque | 100 Go libres | SSD 256 Go (les SSD sont 5× plus rapides) |
| Réseau | Wi-Fi stable | Câble Ethernet (plus fiable pour un serveur) |

> ⚠️ **Cette machine est le serveur.** Ne l'éteignez pas en pleine journée. Installez-la dans un endroit sécurisé mais ventilé.

### 1.2 Logiciels à installer (les 3 seuls programmes nécessaires)

**Vous n'avez pas besoin d'installer Python, PostgreSQL, Redis, Nginx ou WeasyPrint manuellement.** Docker s'occupe de tout cela automatiquement.

| Logiciel | Rôle | Version minimale | Téléchargement |
|----------|------|------------------|----------------|
| **Docker Desktop** | Fait tourner l'application dans des conteneurs isolés | 4.30+ | https://www.docker.com/products/docker-desktop/ |
| **Git** | Récupère les mises à jour du code source | 2.40+ | https://git-scm.com/download/win |
| **Navigateur web** | Interface utilisateur de YELEN SCHOOL | Chrome 120+, Firefox 120+, Edge 120+ | (déjà installé) |

> 💡 **Astuce :** Installez aussi **7-Zip** (https://7-zip.org/) si vous recevez les mises à jour sous forme d'archive ZIP.

### 1.3 Ce que chaque logiciel fait — Pour les curieux

| Technologie | À quoi ça sert ? |
|-------------|------------------|
| **Django 4.2 + Gunicorn** | Le cœur de l'application — Gunicorn est le serveur WSGI professionnel (4 workers, timeouts) qui fait tourner Django en production |
| **PostgreSQL 15** | La base de données — stocke TOUTES les données (élèves, notes, paiements) |
| **Redis 7** | Le cache — accélère l'application en mémorisant les données fréquentes |
| **Nginx** | Le serveur web frontal — gère le HTTPS (certificat auto-signé), la terminaison SSL, et sert les fichiers statiques |
| **WeasyPrint** | Générateur de PDF — produit les bulletins, certificats, listes |
| **MinIO** | Stockage de fichiers — photos des élèves, documents justificatifs |

### 1.4 Accès réseau nécessaire

| Situation | Internet requis ? | Détail |
|-----------|-------------------|--------|
| Installation initiale | **Oui** | Pour télécharger Docker, Git et les images Docker |
| Mise à jour | **Oui** | Pour télécharger la nouvelle version ou reconstruire l'image |
| Usage quotidien | **Non** | L'application fonctionne 100 % en local sur le réseau de l'établissement |
| Fonctionnalités IA (analyse de décrochage) | Optionnel | Seulement si vous utilisez l'IA — nécessite une clé API Anthropic |

> 💡 **Réseau local uniquement :** YELEN SCHOOL est conçu pour fonctionner sans Internet. Toutes les données restent sur votre serveur.

---

## 2. Préparation de la machine — Installation des outils

### 2.1 Activer la virtualisation (indispensable pour Docker)

1. Ouvrez le **Gestionnaire des tâches** (`Ctrl + Shift + Échap`)
2. Allez dans l'onglet **Performances**
3. Cliquez sur **Processeur**
4. Vérifiez que **Virtualisation : Activé** s'affiche en bas à droite

**Si la virtualisation est désactivée :**
- Redémarrez la machine
- Au démarrage, appuyez sur `F2`, `F10`, `F12` ou `Suppr` (selon votre marque) pour entrer dans le BIOS/UEFI
- Cherchez "Intel VT-x", "AMD-V" ou "Virtualization Technology" et activez-le
- Sauvegardez (`F10`) et redémarrez

> ❓ **Si vous ne trouvez pas :** contactez le fournisseur de votre ordinateur ou cherchez "[Marque PC] activer virtualisation BIOS" sur Google.

### 2.2 Installer Docker Desktop

1. Téléchargez depuis : https://www.docker.com/products/docker-desktop/
2. Lancez l'installeur (`Docker Desktop Installer.exe`)
3. **Laissez toutes les options par défaut** — ne changez rien
4. Quand l'installation demande de redémarrer, acceptez
5. Après redémarrage, Docker Desktop se lance automatiquement
6. Attendez que l'icône de la baleine dans la barre des tâches soit **verte** (et non orange ou rouge)

**Vérification :** Ouvrez un terminal (`cmd`) et tapez :

```cmd
docker --version
```

Résultat attendu (exemple) :
```
Docker version 27.3.1, build xxxxxxx
```

> ❓ **Si ça ne marche pas :** redémarrez la machine. Si l'icône reste orange, allez dans le menu Démarrer → "Docker Desktop" → cliquez "Start".

### 2.3 Installer Git

1. Téléchargez depuis : https://git-scm.com/download/win
2. Lancez l'installeur — **laissez toutes les options par défaut**
3. Vérifiez :

```cmd
git --version
```

Résultat attendu :
```
git version 2.45.0.windows.1
```

---

## 3. Installation pas à pas — Mise en place de l'application

### 3.1 Choisir le dossier d'installation

**Règle importante :** le chemin du dossier ne doit contenir ni espaces, ni accents, ni caractères spéciaux.

| Correct | Incorrect |
|---------|-----------|
| `E:\yelen-school\` | `C:\Users\Jean Paul\Bureau\yelen school\` |
| `C:\yelen-school\` | `D:\école\app\` |

**Chemin recommandé :** `E:\yelen-school\` (si le disque E: existe) ou `C:\yelen-school\`

### 3.2 Créer le dossier d'installation

Ouvrez le terminal **en tant qu'administrateur** :
1. Cliquez sur le menu Démarrer
2. Tapez `cmd`
3. Clic droit → "Exécuter en tant qu'administrateur"

```cmd
E:
mkdir E:\yelen-school
cd E:\yelen-school
```

> *(Si vous utilisez `C:`, remplacez `E:` par `C:`)*

### 3.3 Récupérer le code source

**Méthode A — Par Git (recommandé pour les mises à jour faciles) :**

```cmd
git clone [URL_DU_DÉPÔT] E:\yelen-school
```

> Remplacez `[URL_DU_DÉPÔT]` par l'adresse Git fournie par l'équipe YELEN SCHOOL. Exemple : `https://github.com/votre-organisation/yelen-school.git`

**Méthode B — Par archive ZIP :**

1. Décompressez l'archive ZIP dans `E:\yelen-school\`
2. Vérifiez que les fichiers sont directement dans ce dossier (pas dans un sous-dossier)

### 3.4 Vérifier la présence des fichiers essentiels

```cmd
dir
```

Vous devez voir ces fichiers :

```
Dockerfile              ← L'emballage de l'application (utilise Gunicorn en production)
docker-compose.dev.yml  ← La recette pour tout lancer
manage.py               ← Le cœur Django (ne pas toucher)
.env                    ← Vos paramètres secrets (à configurer)
.env.example            ← Template de configuration (à copier si .env absent)
.dockerignore           ← Exclut les fichiers inutiles du conteneur Docker
README.md               ← Présentation du projet
entrypoint.sh           ← Script de démarrage (migrate + collectstatic automatiques)
```

> ⚠️ **Si `.env` est absent :** copiez `.env.example` vers `.env` et modifiez-le (voir section 4).

### 3.5 Structure du projet — Où sont les choses ?

```
E:\yelen-school\
├── Dockerfile                 # Instructions pour construire l'image (Gunicorn WSGI)
├── docker-compose.dev.yml     # Configuration des services
├── manage.py                  # Point d'entrée Django
├── .env                       # Variables d'environnement (SECRET)
├── .env.example               # Template du fichier .env (documentation)
├── .dockerignore              # Exclut .git, .env, caches du contexte Docker
├── entrypoint.sh              # Script de démarrage (migrate + collectstatic)
├── README.md                  # Présentation du projet
│
├── yelen_school/              # Configuration Django
│   └── settings.py            # Paramètres de l'application
│
├── templates/                 # Pages HTML
├── static/                    # CSS, JavaScript, images (source)
├── staticfiles/               # Fichiers statiques collectés (servis par Nginx)
├── media/                     # Fichiers uploadés (photos, documents)
│
├── accounts/                  # Gestion des comptes
├── eleves/                    # Gestion des élèves
├── personnel/                 # Gestion du personnel
├── pedagogie/                 # Notes, matières, classes
├── finances/                  # Paiements, frais scolaires
├── bulletins/                 # Génération des bulletins PDF
├── presences/                 # Appel et présence
├── examens/                   # Examens et compositions
├── documents/                 # Documents administratifs
├── parametres/                # Configuration de l'établissement
├── communication/             # SMS, emails
│
├── nginx/                     # Configuration du serveur web
│   └── default.conf           # Règles Nginx (proxy inverse + fichiers statiques)
│
├── requirements/              # Dépendances Python
│   └── base.txt               # Liste des bibliothèques (inclut gunicorn)
│
└── docs/                      # Documentation
    └── GUIDE_DEPLOIEMENT_WINDOWS.md  ← Ce document
```

---

## 4. Configuration des fichiers sensibles (.env)

### 4.1 Qu'est-ce que le fichier .env ?

Le fichier `.env` contient **tous les secrets** de l'application : mots de passe, clés, adresses. Il est lu au démarrage de l'application. **Sans lui, rien ne fonctionne.**

> 💡 **Un template est disponible :** `.env.example` à la racine du projet. Copiez-le et adaptez-le :
> ```cmd
> copy .env.example .env
> ```

> ⚠️ **Ne partagez JAMAIS ce fichier.** Il contient les mots de passe de votre établissement.
> ⚠️ **Ne le mettez JAMAIS dans une archive ZIP envoyée par email.**
> ⚠️ **Gardez-en une copie papier dans un coffre** (ou un gestionnaire de mots de passe).

### 4.2 Ouvrir et modifier le fichier .env

```cmd
notepad E:\yelen-school\.env
```

### 4.3 Configuration détaillée — Ligne par ligne

Voici chaque ligne expliquée, avec ce que vous devez mettre :

```dotenv
# ═══════════════════════════════════════════════
# SÉCURITÉ — Ces 3 valeurs sont OBLIGATOIRES
# ═══════════════════════════════════════════════

# Clé secrète Django — empêche la falsification des sessions et cookies
# Générez-en une ici : https://djecrety.ir/
# Cliquez "Generate", copiez le résultat, collez-le ici (longue chaîne de caractères)
SECRET_KEY=ceci_est_une_tres_longue_chaine_aleatoire_de_50_caracteres_minimum

# Mode débogage — DOIT être False en production
# True = affiche les erreurs techniques détaillées (dangereux, à ne pas laisser activé)
DEBUG=False

# Hôtes autorisés — liste des adresses qui peuvent accéder à l'application
# Séparez chaque adresse par une virgule (sans espace)
# Exemple : ALLOWED_HOSTS=localhost,127.0.0.1,192.168.1.100
ALLOWED_HOSTS=localhost,127.0.0.1

# Origines CSRF autorisées — mêmes valeurs que ALLOWED_HOSTS mais avec https://
# Séparez chaque origine par une virgule
# Exemple : CSRF_TRUSTED_ORIGINS=https://localhost,https://192.168.1.100
CSRF_TRUSTED_ORIGINS=https://localhost,https://127.0.0.1

# ═══════════════════════════════════════════════
# BASE DE DONNÉES (PostgreSQL)
# ═══════════════════════════════════════════════

DB_NAME=yelen_school_db          # Nom de la base (laissez par défaut)
DB_USER=yelen_user               # Identifiant (laissez par défaut)
DB_PASSWORD=choisissez_un_mot_de_passe_fort_ici  # ← CHANGEZ CECI !
DB_HOST=db                       # Hôte = nom du conteneur Docker (ne pas modifier)
DB_PORT=5432                     # Port standard PostgreSQL (ne pas modifier)

# ═══════════════════════════════════════════════
# CACHE (Redis) — Accélère l'application
# ═══════════════════════════════════════════════

REDIS_URL=redis://redis:6379/0   # Ne pas modifier

# ═══════════════════════════════════════════════
# STOCKAGE DES FICHIERS (MinIO)
# ═══════════════════════════════════════════════

MINIO_ENDPOINT=minio:9000        # Ne pas modifier
MINIO_ACCESS_KEY=yelenaccess     # Identifiant (peut rester par défaut)
MINIO_SECRET_KEY=changez_moi_aussi             # ← CHANGEZ CECI
MINIO_BUCKET=yelen-documents     # Dossier de stockage (ne pas modifier)

# ═══════════════════════════════════════════════
# EMAIL — Envoi de notifications
# ═══════════════════════════════════════════════

# En développement : MailHog (interface visible sur http://localhost:8025)
# En production : remplacez par un vrai serveur SMTP
EMAIL_HOST=mailhog
EMAIL_PORT=1025

# ═══════════════════════════════════════════════
# SMS — Notifications par SMS aux parents
# ═══════════════════════════════════════════════

# Mettez False si vous n'utilisez pas les SMS
SMS_ENABLED=False
SMS_BACKEND=http

# Si vous utilisez l'app Android "SMS Gateway" sur le réseau WiFi :
SMS_HTTP_URL=http://192.168.X.X:8080/message   # ← Adresse du téléphone
SMS_HTTP_USER=admin
SMS_HTTP_PASSWORD=votre_mot_de_passe_sms

# ═══════════════════════════════════════════════
# MODEM GSM (alternative aux SMS)
# ═══════════════════════════════════════════════

SMS_MODEM_PORT=COM3              # Port série du modem
SMS_MODEM_BAUD=9600              # Vitesse de communication
SMS_MODEM_TIMEOUT=10

# ═══════════════════════════════════════════════
# IA — Analyse du risque de décrochage (optionnel)
# Nécessite une connexion Internet
# ═══════════════════════════════════════════════

# Laissez vide si vous n'utilisez pas l'IA
ANTHROPIC_API_KEY=
```

### 4.4 Synchroniser les mots de passe

Le mot de passe de la base de données doit être le **même** à deux endroits :

1. **Dans `.env`** : `DB_PASSWORD=...` (utilisé par Django pour se connecter)
2. **Dans `docker-compose.dev.yml`** : `POSTGRES_PASSWORD=...` (utilisé par PostgreSQL)

Pour modifier le `docker-compose.dev.yml` :

```cmd
notepad E:\yelen-school\docker-compose.dev.yml
```

Cherchez la section `db:` et remplacez la ligne `POSTGRES_PASSWORD` :

```yaml
  db:
    image: postgres:15
    environment:
      POSTGRES_DB: yelen_school_db
      POSTGRES_USER: yelen_user
      POSTGRES_PASSWORD: choisissez_un_mot_de_passe_fort_ici  ← MÊME VALEUR QUE DB_PASSWORD
```

### 4.5 Checklist de sécurité .env

Avant de continuer, vérifiez :

- [ ] `DEBUG=False` (jamais True en production)
- [ ] `SECRET_KEY` est une longue chaîne aléatoire (50+ caractères)
- [ ] `DB_PASSWORD` est un mot de passe fort (lettres + chiffres + symboles)
- [ ] `MINIO_SECRET_KEY` est changé
- [ ] `SMS_ENABLED=False` si vous n'utilisez pas les SMS
- [ ] `ALLOWED_HOSTS` contient au moins `localhost,127.0.0.1`
- [ ] `CSRF_TRUSTED_ORIGINS` correspond aux adresses utilisées (avec `https://`)

---

## 5. Premier démarrage et vérification

### 5.1 Démarrer l'application pour la première fois

Depuis le dossier `E:\yelen-school\` :

```cmd
docker compose -f docker-compose.dev.yml up --build -d
```

**Ce que fait cette commande :**

| Partie | Explication |
|--------|-------------|
| `docker compose -f docker-compose.dev.yml` | Utilise le fichier de configuration |
| `--build` | Construit l'image de l'application (nécessaire la 1ʳᵉ fois ou après une mise à jour) |
| `-d` | Mode "détaché" = en arrière-plan (vous gardez la main sur le terminal) |

> ⏳ **Premier lancement : 5 à 15 minutes.** Docker télécharge PostgreSQL, Redis, Nginx, MinIO, MailHog, puis construit l'application Django avec toutes ses dépendances.

**Pour voir la progression en temps réel :**

```cmd
docker compose -f docker-compose.dev.yml logs -f
```

> Appuyez sur `Ctrl + C` pour arrêter d'afficher les logs (l'application continue de tourner).

### 5.2 Vérifier que tous les services sont démarrés

```cmd
docker compose -f docker-compose.dev.yml ps
```

Résultat attendu (tous les services doivent être `Up`) :

```
NAME                    STATUS          PORTS
yelen-school-web-1      Up              0.0.0.0:8000->8000/tcp
yelen-school-db-1       Up (healthy)    0.0.0.0:5432->5432/tcp
yelen-school-redis-1    Up              6379/tcp
yelen-school-nginx-1    Up              0.0.0.0:80->80/tcp, 0.0.0.0:443->443/tcp
yelen-school-minio-1    Up              0.0.0.0:9000->9000/tcp
yelen-school-mailhog-1  Up              0.0.0.0:8025->8025/tcp
```

> ⚠️ **Si un service est `Exit` ou `Restarting`** → voir section [Erreurs fréquentes](#11-erreurs-fréquentes-et-résolution-troubleshooting).

### 5.3 Créer les tables dans la base de données (migrations)

**Les migrations sont automatiques** — l'entrypoint du conteneur (`entrypoint.sh`) exécute `python manage.py migrate` à chaque démarrage. Vous n'avez normalement rien à faire.

Si vous devez les forcer manuellement (après un changement de version, par exemple) :

```cmd
docker compose -f docker-compose.dev.yml exec web python manage.py migrate
```

Résultat attendu (exemple) :
```
Operations to perform:
  Apply all migrations: accounts, admin, auth, bulletins, ...
Running migrations:
  Applying accounts.0001_initial... OK
  Applying eleves.0001_initial... OK
  Applying pedagogie.0001_initial... OK
  ...
```

> ❓ **S'il y a des erreurs :** exécutez à nouveau la commande. Parfois la base de données n'est pas encore prête.

### 5.4 Créer le compte administrateur (premier utilisateur)

C'est le compte qui vous permettra de vous connecter pour la première fois.

```cmd
docker compose -f docker-compose.dev.yml exec web python manage.py createsuperuser
```

Le programme vous pose ces questions :

| Question | Ce qu'il faut saisir |
|----------|---------------------|
| `Email:` | L'adresse email du directeur (ex: `directeur@etablissement.bf`) |
| `Nom:` | Nom de famille de l'administrateur |
| `Prénom:` | Prénom de l'administrateur |
| `Password:` | Mot de passe (ne s'affiche pas à l'écran — c'est normal) |
| `Password (again):` | Même mot de passe |

> 💡 **Notez précieusement ces identifiants.** Si vous les perdez, il faudra réinitialiser le mot de passe par la ligne de commande.

### 5.5 Collecter les fichiers statiques (CSS, icônes, images)

**La collecte est automatique** — l'entrypoint du conteneur exécute `python manage.py collectstatic --noinput --clear` à chaque démarrage. Les fichiers sont copiés dans `staticfiles/` et servis directement par Nginx via l'alias `/static/`.

Si vous devez forcer la collecte manuellement :

```cmd
docker compose -f docker-compose.dev.yml exec web python manage.py collectstatic --noinput
```

### 5.6 Premier test depuis le navigateur

Ouvrez votre navigateur et allez sur :

```
http://localhost:8000/accounts/login/
```

Vous devez voir la page de connexion de YELEN SCHOOL (fond bleu foncé `#0A1628`, logo vert).

> 💡 **Alternative HTTPS :** Si vous passez par Nginx (port 443), utilisez :
> ```
> https://localhost/accounts/login/
> ```
> ⚠️ Le certificat SSL est auto-signé — le navigateur affichera un avertissement de sécurité. Cliquez sur "Avancé" → "Continuer vers localhost" (c'est normal et sécurisé pour un usage en réseau local).

Connectez-vous avec l'email et le mot de passe créés à l'étape 5.4.

---

## 6. Procédure de vérification post-déploiement

### 6.1 Vérification rapide (2 minutes)

Exécutez ces tests dans l'ordre :

```cmd
REM 1. Vérifier l'état des conteneurs
docker compose -f docker-compose.dev.yml ps

REM 2. Vérifier la connexion à la base de données
docker compose -f docker-compose.dev.yml exec web python manage.py check --database default

REM 3. Afficher les 20 dernières lignes de logs
docker compose -f docker-compose.dev.yml logs web --tail=20
```

### 6.2 Vérification fonctionnelle complète (10 minutes)

Cochez chaque point après l'avoir testé :

- [ ] **Page de connexion** — `http://localhost:8000/accounts/login/` (ou `https://localhost/`) s'affiche (fond sombre, pas de page blanche)
- [ ] **Connexion** — l'email et le mot de passe fonctionnent
- [ ] **Tableau de bord** — les menus principaux s'affichent après connexion
- [ ] **Paramètres** — la page `Paramètres` se charge
- [ ] **Élèves** — la liste des élèves s'affiche (vide au début, c'est normal)
- [ ] **Création d'un élève** — créez un élève test, le matricule `BF-2026-00001` est généré automatiquement
- [ ] **PDF** — générez un bulletin PDF ou un certificat, le fichier se télécharge
- [ ] **Déconnexion** — le bouton de déconnexion fonctionne

### 6.3 Vérifications avancées (administrateur système)

```cmd
REM Vérifier que Redis répond
docker compose -f docker-compose.dev.yml exec redis redis-cli ping
```
Résultat attendu : `PONG`

```cmd
REM Vérifier que PostgreSQL accepte les connexions
docker compose -f docker-compose.dev.yml exec db pg_isready -U yelen_user -d yelen_school_db
```
Résultat attendu : `localhost:5432 - accepting connections`

```cmd
REM Vérifier que le serveur web répond
curl -I http://localhost:8000/accounts/login/
```
Résultat attendu : `HTTP/1.1 200 OK`

### 6.4 Vérification réseau (accès depuis d'autres postes)

Depuis un **autre ordinateur** du réseau local, ouvrez le navigateur et tapez :

```
http://[ADRESSE_IP_DU_SERVEUR]:8000/accounts/login/
```

Par exemple : `http://192.168.1.100:8000/accounts/login/`

Si la page ne s'affiche pas, voir la section [10. Accès depuis les autres postes](#10-accès-depuis-les-autres-postes-du-réseau).

---

## 7. Utilisation au quotidien — Lancer et arrêter l'application

### 7.1 Démarrer l'application

**Méthode simple (double-clic) :**
- Ouvrez l'Explorateur Windows
- Allez dans `E:\yelen-school\`
- Double-cliquez sur `lancer-yelen.bat` (si le fichier existe) ou lancez la commande ci-dessous
- Attendez 1-2 minutes que Docker démarre
- Le navigateur s'ouvre automatiquement sur la page de connexion

> 💡 Créez un raccourci de `lancer-yelen.bat` sur le Bureau pour un accès encore plus rapide.

**Méthode terminal :**
```cmd
docker compose -f docker-compose.dev.yml up -d
```

### 7.2 Arrêter l'application

```cmd
docker compose -f docker-compose.dev.yml down
```

> ⚠️ **Ne jamais éteindre la machine sans avoir arrêté Docker.** Cela peut corrompre la base de données.

**Procédure correcte avant d'éteindre le serveur le soir :**

1. Ouvrez un terminal
2. Tapez : `docker compose -f docker-compose.dev.yml down`
3. Attendez le message : `Network yelen-school_default removed`
4. *Puis* éteignez la machine

### 7.3 Voir l'état des services

```cmd
docker compose -f docker-compose.dev.yml ps
```

Interprétation :

| Statut | Signification |
|--------|---------------|
| `Up` | ✅ Fonctionne correctement |
| `Up (healthy)` | ✅ Fonctionne et est vérifié comme sain |
| `Restarting` | ❌ Plante en boucle — voir troubleshooting |
| `Exit` | ❌ Arrêté — voir troubleshooting |

### 7.4 Consulter les logs (journaux d'événements)

```cmd
REM Tous les services en temps réel
docker compose -f docker-compose.dev.yml logs -f

REM Un seul service
docker compose -f docker-compose.dev.yml logs -f web
docker compose -f docker-compose.dev.yml logs -f db
docker compose -f docker-compose.dev.yml logs -f nginx

REM Dernières 50 lignes (utile pour le support)
docker compose -f docker-compose.dev.yml logs --tail=50
```

> Appuyez sur `Ctrl + C` pour quitter l'affichage des logs.

### 7.5 Commandes utiles au quotidien

| Action | Commande |
|--------|----------|
| Appliquer les migrations | `docker compose exec web python manage.py migrate` |
| Créer un nouvel utilisateur | `docker compose exec web python manage.py createsuperuser` |
| Réinitialiser un mot de passe | `docker compose exec web python manage.py changepassword` |
| Ouvrir le shell Django (expert) | `docker compose exec web python manage.py shell` |
| Redémarrer seulement le serveur web | `docker compose restart web` |
| Voir l'utilisation disque de Docker | `docker system df` |

---

## 8. Sauvegarde et restauration de la base de données

### 8.1 Pourquoi sauvegarder est critique

**Toutes les données sont dans la base PostgreSQL :** élèves, notes, paiements, inscriptions, bulletins.

| Incident | Conséquence sans sauvegarde |
|----------|-----------------------------|
| Panne disque dur | ✅ **Perte totale :** toutes les données |
| Corruption base | ✅ **Perte totale :** à reconstruire à la main |
| Erreur humaine (suppression) | ✅ **Perte :** données irrécupérables |
| Vol de la machine | ✅ **Perte totale :** aucune donnée |

**Règle d'or :** 3 sauvegardes, sur 2 supports différents, dont 1 hors site.
- 1 copie sur le disque du serveur (sauvegarde automatique quotidienne)
- 1 copie sur une clé USB / disque dur externe (hebdomadaire)
- 1 copie dans un endroit différent de la machine (chez le directeur, par exemple)

### 8.2 Sauvegarder la base de données (commande unique)

Ouvrez PowerShell **en administrateur** et tapez :

```powershell
$date = Get-Date -Format "yyyyMMdd_HHmm"
docker compose -f E:\yelen-school\docker-compose.dev.yml exec -T db pg_dump -U yelen_user -d yelen_school_db -Fc > "E:\sauvegardes\sauvegarde_$date.dump"
```

Ce que fait cette commande :

| Partie | Rôle |
|--------|------|
| `pg_dump -U yelen_user -d yelen_school_db` | Exporte toute la base |
| `-Fc` | Format compressé (fichier plus petit) |
| `exec -T` | Exécute dans le conteneur (le `-T` est important dans PowerShell) |
| `> sauvegarde.dump` | Sauvegarde le fichier sur le disque Windows (pas dans Docker) |

> 💡 **Le fichier est directement sur votre disque Windows**, pas à l'intérieur du conteneur Docker. Vous pouvez le copier, le mettre sur une clé USB, l'envoyer — c'est un fichier normal.

### 8.3 Mettre en place la sauvegarde automatique quotidienne

Nous allons configurer Windows pour lancer une sauvegarde chaque soir à 22h00.

**Étape 1 : Créer le dossier de sauvegardes**

```cmd
mkdir E:\sauvegardes
```

**Étape 2 : Créer le script de sauvegarde**

Créez le fichier `E:\sauvegardes\sauvegarder-yelen.ps1` avec ce contenu :

```powershell
# Script de sauvegarde automatique YELEN SCHOOL
# Lancé chaque soir par le Planificateur de tâches

$date = Get-Date -Format "yyyyMMdd_HHmm"
$dossier = "E:\sauvegardes"
$fichier = "$dossier\sauvegarde_$date.dump"

Write-Host "Début de la sauvegarde : $date"

# Sauvegarder la base
docker compose -f E:\yelen-school\docker-compose.dev.yml exec -T db pg_dump -U yelen_user -d yelen_school_db -Fc > $fichier

# Vérifier que la sauvegarde a fonctionné
if ($?) {
    Write-Host "Sauvegarde réussie : $fichier"
    
    # Garder seulement les 30 dernières sauvegardes
    $anciens = Get-ChildItem "$dossier\sauvegarde_*.dump" | Sort-Object LastWriteTime -Descending | Select-Object -Skip 30
    foreach ($a in $anciens) {
        Remove-Item $a.FullName
        Write-Host "Suppression ancienne sauvegarde : $($a.Name)"
    }
} else {
    Write-Host "ERREUR : la sauvegarde a échoué !"
    exit 1
}
```

**Étape 3 : Programmer la tâche dans Windows**

1. Ouvrez le **Planificateur de tâches** (Démarrer → tapez "Planificateur de tâches")
2. Cliquez sur **"Créer une tâche de base..."** (à droite)

Remplissez :

| Champ | Valeur |
|-------|--------|
| Nom | `Sauvegarde YELEN SCHOOL` |
| Description | `Sauvegarde automatique quotidienne de la base de données` |
| Déclencheur | **Tous les jours** |
| Heure | `22:00:00` |
| Action | **Démarrer un programme** |
| Programme | `powershell.exe` |
| Arguments | `-NoProfile -ExecutionPolicy Bypass -File E:\sauvegardes\sauvegarder-yelen.ps1` |
| ✅ Ouvrir la boîte de dialogue Propriétés | Cochez cette case |

3. Cliquez sur **Terminer**
4. Dans la fenêtre des propriétés, cochez **"Exécuter avec les privilèges les plus élevés"**
5. OK

> 💡 **Testez la tâche :** clic droit sur la tâche → **Exécuter**. Vérifiez que le fichier apparaît dans `E:\sauvegardes\`.

### 8.4 Vérifier qu'une sauvegarde est valide

```cmd
docker compose -f docker-compose.dev.yml exec db pg_restore --list /tmp/sauvegarde.dump
```

Si la commande affiche une liste de tables (`eleves_eleve`, `parametres_classe`, ...), la sauvegarde est valide.

**Test plus simple :** vérifiez que le fichier `.dump` n'est pas vide (taille > 1 Ko) :

```cmd
dir E:\sauvegardes\*.dump
```

### 8.5 Restaurer la base de données (en cas de panne)

> ⚠️ **La restauration ÉCRASE toutes les données actuelles.** Utilisez-la uniquement en cas de :
> - Corruption de la base
> - Incident grave (suppression massive par erreur)
> - Migration vers une nouvelle machine

**Procédure complète :**

```cmd
REM Étape 1 : Copier le fichier de sauvegarde dans le conteneur PostgreSQL
docker compose -f docker-compose.dev.yml cp E:\sauvegardes\sauvegarde_20260623.dump db:/tmp/sauvegarde.dump

REM Étape 2 : Supprimer l'ancienne base et en créer une nouvelle vide
docker compose -f docker-compose.dev.yml exec db dropdb -U yelen_user yelen_school_db
docker compose -f docker-compose.dev.yml exec db createdb -U yelen_user yelen_school_db

REM Étape 3 : Restaurer la sauvegarde dans la nouvelle base
docker compose -f docker-compose.dev.yml exec db pg_restore -U yelen_user -d yelen_school_db /tmp/sauvegarde.dump

REM Étape 4 : Redémarrer l'application
docker compose -f docker-compose.dev.yml restart web
```

> Si `dropdb` échoue parce que d'autres connexions sont actives, arrêtez d'abord le serveur web :
> ```cmd
> docker compose -f docker-compose.dev.yml stop web
> ```
> Puis refaites les étapes 2 à 4.

### 8.6 Sauvegarder aussi le fichier .env

Le fichier `.env` contient vos mots de passe. Perdre ce fichier = impossible de redémarrer l'application.

```cmd
copy E:\yelen-school\.env E:\sauvegardes\.env.backup
```

Ajoutez cette ligne à votre script `sauvegarder-yelen.ps1` pour qu'elle soit exécutée automatiquement.

### 8.7 Plan de sauvegarde recommandé

| Fréquence | Quoi | Où |
|-----------|------|-----|
| Tous les jours (22h00) | Sauvegarde complète de la BDD | `E:\sauvegardes\` (automatique) |
| Toutes les semaines | Copier les sauvegardes | Clé USB ou disque dur externe |
| Tous les mois | Copier les sauvegardes + .env | Chez le directeur / coffre |

---

## 9. Procédure de mise à jour — Nouvelle version

Quand l'équipe YELEN SCHOOL vous fournit une nouvelle version, suivez ces étapes dans l'ordre.

### 9.1 Étape 0 — Lire les notes de version

Avant toute mise à jour, lisez le fichier `CHANGELOG.md` ou les notes fournies avec la nouvelle version. Certaines mises à jour peuvent nécessiter des actions supplémentaires.

### 9.2 Étape 1 — Sauvegarder avant tout !

```powershell
$date = Get-Date -Format "yyyyMMdd_HHmm"
docker compose -f E:\yelen-school\docker-compose.dev.yml exec -T db pg_dump -U yelen_user -d yelen_school_db -Fc > "E:\sauvegardes\avant_maj_$date.dump"
```

> ⚠️ **Ne sautez jamais cette étape.** Si la mise à jour échoue, vous pourrez revenir en arrière.

### 9.3 Étape 2 — Arrêter l'application

```cmd
docker compose -f docker-compose.dev.yml down
```

### 9.4 Étape 3 — Remplacer le code source

**Méthode A — Avec Git (recommandé) :**

```cmd
cd E:\yelen-school
git pull origin main
```

**Méthode B — Avec une archive ZIP :**

1. Sauvegardez le fichier `.env` ailleurs (sur le Bureau, par exemple)
2. Supprimez tout le contenu de `E:\yelen-school\` **sauf** le dossier `E:\sauvegardes\`
3. Décompressez la nouvelle archive dans `E:\yelen-school\`
4. Remettez votre fichier `.env` à sa place

### 9.5 Étape 4 — Reconstruire et redémarrer

```cmd
REM Reconstruire l'image Docker (prend les nouvelles dépendances)
docker compose -f docker-compose.dev.yml build

REM Démarrer tous les services
docker compose -f docker-compose.dev.yml up -d
```

### 9.6 Étape 5 — Appliquer les nouvelles migrations

Si la nouvelle version modifie la structure de la base de données, il faut appliquer les migrations :

```cmd
docker compose -f docker-compose.dev.yml exec web python manage.py migrate
```

### 9.7 Étape 6 — Mettre à jour les fichiers statiques

**Automatique** : la collecte des fichiers statiques est exécutée à chaque démarrage du conteneur (via `entrypoint.sh`). Un simple redémarrage suffit :

```cmd
docker compose -f docker-compose.dev.yml restart web
```

Si vous voulez forcer la collecte immédiatement :

```cmd
docker compose -f docker-compose.dev.yml exec web python manage.py collectstatic --noinput --clear
```

### 9.8 Étape 7 — Vérifier que tout fonctionne

Refaites la [vérification rapide (section 6.1)](#61-vérification-rapide-2-minutes) et la [vérification fonctionnelle (section 6.2)](#62-vérification-fonctionnelle-complète-10-minutes).

### 9.9 En cas de problème après la mise à jour

**Si l'application ne fonctionne pas :**

```cmd
REM 1. Voir les erreurs
docker compose -f docker-compose.dev.yml logs web --tail=100

REM 2. Revenir à la version précédente
docker compose -f docker-compose.dev.yml down

REM → Réinstallez l'ancien code source
REM → Redémarrez
REM → Restaurez la sauvegarde (section 8.5)
```

---

## 10. Accès depuis les autres postes du réseau

### 10.1 Principe

Plusieurs personnes doivent utiliser YELEN SCHOOL en même temps :
- Le secrétaire depuis son bureau
- Le directeur depuis son bureau  
- Le comptable depuis son poste

Tous accèdent à la même application via le réseau local. **Seule la machine serveur a besoin de Docker et de l'application installés.** Les autres postes utilisent simplement un navigateur web.

### 10.2 Trouver l'adresse IP du serveur

Sur la **machine serveur**, ouvrez un terminal et tapez :

```cmd
ipconfig
```

Cherchez la section **Carte Ethernet** (ou **Carte réseau sans fil Wi-Fi**) et notez la ligne :

```
   Adresse IPv4. . . . . . . . . . : 192.168.1.100
```

Exemple d'adresses possibles : `192.168.1.42`, `10.0.0.5`, `172.16.0.10`.

> 💡 Notez cette adresse, vous en aurez besoin à chaque fois.

### 10.3 Ajouter l'adresse IP dans le fichier .env

```cmd
notepad E:\yelen-school\.env
```

Trouvez les lignes `ALLOWED_HOSTS` et `CSRF_TRUSTED_ORIGINS` et ajoutez l'adresse IP du serveur :

```dotenv
ALLOWED_HOSTS=localhost,127.0.0.1,192.168.1.100
CSRF_TRUSTED_ORIGINS=https://localhost,https://127.0.0.1,https://192.168.1.100
```

Redémarrez l'application :

```cmd
docker compose -f docker-compose.dev.yml restart web
```

### 10.4 Accéder depuis un autre ordinateur

Sur les autres postes, ouvrez un navigateur et tapez :

```
http://192.168.1.100:8000/accounts/login/
```

> Si vous passez par Nginx (HTTPS avec certificat auto-signé) : `https://192.168.1.100/accounts/login/`
> ⚠️ Le navigateur affichera un avertissement "Votre connexion n'est pas privée" — cliquez sur **"Avancé" → "Continuer vers 192.168.1.100"**. C'est normal en réseau local.

> Remplacez `192.168.1.100` par l'adresse IP réelle de votre serveur.

### 10.5 Accéder depuis un smartphone ou une tablette

1. Connectez le smartphone au **même réseau Wi-Fi** que le serveur
2. Ouvrez le navigateur (Chrome, Firefox)
3. Tapez l'adresse : `http://192.168.1.100:8000`

### 10.6 Attribuer une adresse IP fixe au serveur (IMPORTANT)

**Problème :** Par défaut, l'adresse IP du serveur peut changer à chaque redémarrage du routeur. Si l'IP change, personne ne peut plus accéder à l'application depuis les autres postes.

**Solution :** Donner une adresse IP fixe au serveur.

**Méthode simple — via les paramètres Windows :**

1. `ipconfig` dans un terminal → notez :
   - **Adresse IPv4** (ex: `192.168.1.100`)
   - **Masque de sous-réseau** (ex: `255.255.255.0`)
   - **Passerelle par défaut** (ex: `192.168.1.1`)
   - **Serveur DNS** (ex: `192.168.1.1`)

2. Allez dans : Paramètres → Réseau et Internet → Wi-Fi (ou Ethernet) → Gérer les réseaux connus → Propriétés IP
3. Passez en **IPv4 manuel**
4. Saisissez les valeurs notées ci-dessus

**Méthode via le routeur (plus stable) :**

1. Connectez-vous à l'interface du routeur (généralement `http://192.168.1.1`)
2. Identifiant : `admin`, Mot de passe : souvent `admin` ou noté sur le routeur
3. Cherchez "Réservation DHCP" ou "Attribution IP fixe"
4. Associez l'adresse MAC du serveur à une IP fixe

### 10.7 Ouvrir le port 8000 dans le pare-feu Windows (si nécessaire)

Si les autres postes ne parviennent pas à accéder à l'application :

```cmd
netsh advfirewall firewall add rule name="YELEN SCHOOL" protocol=TCP dir=in localport=8000 action=allow
```

> Exécutez cette commande une seule fois. Elle autorise les connexions entrantes sur le port 8000.

---

## 11. Erreurs fréquentes et résolution (Troubleshooting)

### 11.1 Docker Desktop ne démarre pas

**Symptôme :** L'icône Docker reste orange ou ne s'affiche pas.

**Solutions dans l'ordre :**

1. Redémarrez la machine complètement
2. Vérifiez que la virtualisation est activée (section 2.1)
3. Mettez à jour WSL 2 :
   ```cmd
   wsl --update
   wsl --set-default-version 2
   ```
4. Réinstallez Docker Desktop (téléchargez la dernière version)

### 11.2 Un conteneur est `Exit` ou `Restarting`

**Méthode de diagnostic :**

```cmd
REM Voir les logs du conteneur qui plante
docker compose -f docker-compose.dev.yml logs db --tail=50
docker compose -f docker-compose.dev.yml logs web --tail=50
```

**Causes courantes et solutions :**

| Symptôme dans les logs | Cause probable | Solution |
|------------------------|---------------|----------|
| `FATAL: password authentication failed` | Mot de passe différent entre `.env` et `docker-compose.dev.yml` | Vérifiez que `DB_PASSWORD` = `POSTGRES_PASSWORD` |
| `could not connect to server: Connection refused` | PostgreSQL n'est pas encore prêt | Attendez 30 secondes, réessayez |
| `port is already allocated` | Un programme utilise déjà le port | Voir section 11.3 |
| `ModuleNotFoundError: No module named 'xxx'` | Dépendance manquante | Reconstruisez l'image : `docker compose up --build` |

### 11.3 Erreur "port is already allocated"

**Symptôme :**
```
Error response from daemon: Ports are not available: exposing port TCP 0.0.0.0:8000 -> ...
```

**Cause :** Un autre programme utilise déjà le port 8000 (un autre serveur web, par exemple).

**Solution :**

```cmd
REM Trouver quel programme bloque
netstat -ano | findstr :8000
```

Notez le PID (dernier nombre, ex: `12345`) et arrêtez-le :

```cmd
taskkill /PID 12345 /F
```

> **Si le PID correspond à un programme important :** changez le port de YELEN SCHOOL dans `docker-compose.dev.yml` (ligne `"8000:8000"` → `"8001:8000"`).

### 11.4 La page web affiche une erreur 500 (Internal Server Error)

**Causes les plus fréquentes :**

| Cause | Vérification | Solution |
|-------|-------------|----------|
| Migrations non appliquées | `docker compose exec web python manage.py migrate` | Exécutez les migrations |
| Fichier .env manquant ou incorrect | `notepad .env` | Vérifiez les valeurs |
| Fichiers statiques non collectés | `docker compose exec web python manage.py collectstatic --noinput` | Collectez les fichiers |
| Base de données injoignable | `docker compose exec db pg_isready -U yelen_user` | Vérifiez que `db` est `Up (healthy)` |

**Diagnostic avancé :**

```cmd
REM Voir l'erreur exacte dans les logs
docker compose -f docker-compose.dev.yml logs web --tail=100
```

Cherchez une ligne avec `Traceback` ou `Error` — c'est là que se trouve la cause réelle.

### 11.5 Impossible de se connecter (identifiants refusés)

**Symptôme :** Message "Identifiants incorrects" sur la page de connexion.

**Solutions :**

1. Utilisez bien l'**adresse email** (pas un nom d'utilisateur)
2. Vérifiez les majuscules/minuscules (le mot de passe est sensible à la casse)
3. Vérifiez que la 2FA n'est pas activée (dans ce cas, un code à 6 chiffres est demandé après le mot de passe)
4. Réinitialisez le mot de passe :
   ```cmd
   docker compose -f docker-compose.dev.yml exec web python manage.py changepassword
   ```

### 11.6 La génération de PDF ne fonctionne pas

**Symptôme :** Le bouton "Télécharger PDF" semble cliqué mais rien ne se passe, ou une erreur s'affiche.

**Diagnostic :**

```cmd
docker compose -f docker-compose.dev.yml logs web --tail=50
```

**Solutions :**

- Si erreur `libpango` ou `libcairo` → reconstruisez l'image Docker :
  ```cmd
  docker compose -f docker-compose.dev.yml down
  docker compose -f docker-compose.dev.yml up --build -d
  ```

- Si erreur "403 Forbidden" → le fichier est bloqué par le navigateur. Désactivez temporairement les bloqueurs de popup pour ce site.

### 11.7 Perte d'accès au serveur depuis les autres postes

**Symptôme :** Les autres ordinateurs ne peuvent plus accéder à `http://192.168.X.X:8000`.

**Checklist de diagnostic :**

1. L'adresse IP du serveur a-t-elle changé ? → `ipconfig` sur le serveur
2. L'application Docker est-elle démarrée ? → `docker compose ps`
3. Le pare-feu Windows bloque-t-il le port 8000 ? → Voir section 10.7
4. Le serveur est-il allumé ? (Vérification évidente mais nécessaire)

### 11.8 Espace disque insuffisant

**Symptômes :** Erreurs "No space left on device", base de données qui refuse d'écrire, application qui ralentit.

**Vérification :**

```cmd
REM Espace disque global
wmic logicaldisk get size,freespace,caption

REM Espace utilisé par Docker
docker system df
```

**Nettoyage (sans perdre de données) :**

```cmd
REM Supprime les images inutilisées (pas les volumes = pas les données)
docker image prune -a

REM Supprime les conteneurs arrêtés
docker container prune

REM Supprime TOUT ce qui est inutilisé (sauf les volumes)
docker system prune
```

> ⚠️ Ne supprimez JAMAIS les volumes Docker (`docker volume prune`), ils contiennent vos données.

### 11.9 La base de données est corrompue ou ne répond plus

**Symptôme :** `docker compose ps` montre `db Exit 1` ou des messages d'erreur PostgreSQL dans les logs.

**Procédure de récupération :**

```cmd
REM 1. Arrêter tous les services
docker compose -f docker-compose.dev.yml down

REM 2. Redémarrer uniquement la base de données
docker compose -f docker-compose.dev.yml up -d db

REM 3. Attendre qu'elle soit prête (30 secondes)
docker compose -f docker-compose.dev.yml exec db pg_isready -U yelen_user

REM 4. Vérifier l'intégrité de la base
docker compose -f docker-compose.dev.yml exec db psql -U yelen_user -d yelen_school_db -c "SELECT count(*) FROM information_schema.tables;"

REM 5. Si la base répond mais a des problèmes, réparez-la
docker compose -f docker-compose.dev.yml exec db psql -U yelen_user -d yelen_school_db -c "VACUUM FULL ANALYZE;"
```

**Si la base est irrécupérable :**

1. Supprimez le volume PostgreSQL :
   ```cmd
   docker compose -f docker-compose.dev.yml down -v
   ```
   > ⚠️ Cela supprime TOUTES les données. Utilisez seulement si vous avez une sauvegarde.

2. Redémarrez :
   ```cmd
   docker compose -f docker-compose.dev.yml up -d
   ```

3. Restaurez la dernière sauvegarde (section 8.5).

### 11.10 Erreur Git "failed to push some refs"

**Symptôme :** `git pull` échoue avec `error: Your local changes to the following files would be overwritten by merge`.

**Solution :**

```cmd
REM Sauvegarder vos modifications locales (le fichier .env)
copy .env .env.local.backup

REM Annuler les modifications locales pour permettre la mise à jour
git checkout -- .

REM Maintenant le git pull devrait fonctionner
git pull origin main

REM Remettre votre .env
copy .env.local.backup .env
```

---

## 12. Annexes

### 12.1 Carte de référence rapide (à imprimer et coller sur le serveur)

```text
┌──────────────────────────────────────────────────────┐
│            YELEN SCHOOL — AIDE MÉMOIRE                │
│                                                      │
│  DÉMARRER     : docker compose up -d                 │
│  ARRÊTER      : docker compose down                  │
│  ÉTAT         : docker compose ps                    │
│  LOGS         : docker compose logs -f               │
│  MIGRATIONS   : docker compose exec web python       │
│                  manage.py migrate                    │
│  SAUVEGARDER  : (script automatique chaque soir)     │
│  RESTAURER    : (section 8.5 du guide)               │
│  ADRESSE WEB  : http://localhost:8000                │
│                                                      │
│  ⚠️ Arrêter Docker AVANT d'éteindre la machine      │
└──────────────────────────────────────────────────────┘
```

### 12.2 Liste des services, ports et rôles

| Service | Port(s) | Rôle | Visible depuis le réseau ? |
|---------|---------|------|---------------------------|
| **web** (Django + Gunicorn) | 8000 | Application principale (4 workers Gunicorn) | Oui — interface utilisateur |
| **nginx** | 80 → 443 | Proxy HTTPS, SSL auto-signé, sert les fichiers statiques | Oui (443 — HTTPS) |
| **db** (PostgreSQL) | 5432 | Base de données | Non — interne seulement |
| **redis** | 6379 | Cache / sessions | Non — interne seulement |
| **minio** | 9000, 9001 | Stockage fichiers, console admin | Non (9001 accessible si besoin) |
| **mailhog** | 8025 | Simulation email (développement) | Non — test seulement |

### 12.3 Structure des volumes Docker (où sont les données)

| Volume / Montage | Contenu | Emplacement physique (Windows) |
|---------------|---------|-------------------------------|
| `postgres_data` | **Toutes les données** (élèves, notes, paiements) | `\\wsl.localhost\docker\volumes\...` |
| `nginx_certs` | Certificats SSL pour HTTPS | `\\wsl.localhost\docker\volumes\...` |
| `./staticfiles` (bind mount) | Fichiers statiques collectés, servis par Nginx | `E:\yelen-school\staticfiles\` |

> ⚠️ **Ne touchez jamais à ces dossiers directement.** Utilisez toujours les commandes Docker.

### 12.4 Que faire en cas de panne matérielle du serveur

**Scénario :** Le disque dur du serveur est mort, l'ordinateur ne démarre plus.

**Procédure de récupération complète :**

1. **Récupérez la dernière sauvegarde** — soit sur la clé USB, soit dans le dossier `E:\sauvegardes\` (si le disque est encore lisible), soit chez le directeur

2. **Procurez-vous une nouvelle machine** (ou réparez l'ancienne)

3. **Installation propre :**
   - Installez Windows
   - Installez Docker Desktop
   - Installez Git
   - Créez le dossier `E:\yelen-school\`
   - Récupérez le code source (Git clone ou archive ZIP fournie par l'équipe)

4. **Reconfigurez le fichier `.env`** en utilisant vos mots de passe notés

5. **Démarrez l'application :**
   ```cmd
   docker compose -f docker-compose.dev.yml up --build -d
   ```

6. **Restaurer la base de données** (section 8.5)

7. **Vérifiez que tout fonctionne** (section 6)

> ⏱️ **Temps estimé :** 1 à 3 heures selon votre connexion internet et votre maîtrise des outils.

### 12.5 Procédure de test de la restauration (à faire une fois par trimestre)

Pour être certain que vos sauvegardes fonctionnent, testez la restauration une fois par trimestre :

```cmd
REM 1. Arrêter l'application
docker compose -f docker-compose.dev.yml down

REM 2. Redémarrer (cela recrée une base vide)
docker compose -f docker-compose.dev.yml up -d

REM 3. Appliquer les migrations
docker compose -f docker-compose.dev.yml exec web python manage.py migrate

REM 4. Restaurer la sauvegarde
docker compose -f docker-compose.dev.yml cp E:\sauvegardes\sauvegarde_exemple.dump db:/tmp/test.dump
docker compose -f docker-compose.dev.yml exec db pg_restore -U yelen_user -d yelen_school_db /tmp/test.dump

REM 5. Vérifier que les données sont là
docker compose -f docker-compose.dev.yml exec db psql -U yelen_user -d yelen_school_db -c "SELECT count(*) FROM eleves_eleve;"
```

### 12.6 Sécurité — Rappels importants

| Règle | Pourquoi |
|-------|----------|
| `DEBUG=False` en production | `True` affiche les erreurs techniques détaillées, accessible à tous |
| `SECRET_KEY` forte et unique | Protège les sessions, cookies et tokens |
| Mots de passe changés (DB, MinIO) | Empêche les accès non autorisés à la base et aux fichiers |
| Pas de `.env` dans les emails/ZIP | Qui a le `.env` a tous les accès à l'application |
| Sauvegardes régulières | Seule protection contre la perte de données |
| Arrêter Docker avant d'éteindre | Évite la corruption de la base de données |

### 12.7 Support

**Si ce guide ne résout pas votre problème :**

1. Générez un rapport complet :
   ```cmd
   docker compose -f docker-compose.dev.yml logs > E:\sauvegardes\logs_support.txt
   ```
2. Joignez ce fichier à votre demande de support
3. Envoyez à l'équipe YELEN SCHOOL avec une description du problème

**Informations à fournir dans votre demande :**
- Ce que vous essayez de faire
- Ce qui se passe (message d'erreur exact)
- Ce que vous avez déjà essayé
- Le fichier `logs_support.txt`

---

*Document rédigé pour YELEN SCHOOL — Version 4.2 — Juin 2026*

*📘 Guide mis à jour — Section Documentation déploiement*
