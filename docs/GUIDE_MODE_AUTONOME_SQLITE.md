# Guide — Mode autonome (SQLite, sans Docker)

> **Public** : responsable informatique de l'établissement.
> **Objectif** : installer YELEN SCHOOL sur **une machine serveur** de l'école, et
> permettre à **20 postes ou plus** d'y accéder par navigateur, **sans Docker,
> sans PostgreSQL, sans Redis**.

---

## 1. Principe

```
 PC secrétariat ─┐
 PC comptable   ─┤   réseau local (Wi-Fi / câble)      ┌──────────── SERVEUR ────────────┐
 PC direction   ─┼──────── http://192.168.1.10:8000 ───▶│  YELEN SCHOOL (Python)          │
 PC salle profs ─┤                                      │   └─▶ data/yelen_school.sqlite3 │
 … (20+ postes) ─┘                                      └─────────────────────────────────┘
```

- La base de données est **un seul fichier** (`data/yelen_school.sqlite3`) sur le
  disque du serveur. Les postes clients **n'y touchent jamais** : ils parlent au
  serveur web par HTTP, exactement comme avec PostgreSQL.
- Le **même code** fonctionne dans les deux modes ; on choisit par la variable
  `DB_ENGINE` (`sqlite` ou `postgresql`) dans le fichier `.env`.

### Résultats du test de charge (référence)

Test réalisé sur la version 2026-09 avec une base de **1 500 élèves × 5 ans**
(1 080 000 notes, 45 000 paiements, fichier de 513 Mo) et **20 navigateurs
simultanés enchaînant des actions sans pause pendant 90 s** (4 workers, 2 CPU) :

| Indicateur | Résultat |
|---|---|
| Requêtes HTTP traitées | 1 953 (21 req/s soutenues) |
| Erreurs | **0** (aucune erreur « database is locked ») |
| Saisie de 38 notes (POST) — médiane | 2,1 s sous charge maximale, 0,8 s à 5 utilisateurs |
| Pages de consultation — médiane | 0,3 à 0,6 s sous charge maximale |
| Intégrité de la base après le test | `integrity_check = ok`, 0 violation de clé étrangère |

Le facteur limitant était le **processeur** (2 cœurs à 100 %), pas SQLite : la
part « base de données » d'une page typique est de 0 à 50 ms. Un serveur à
4 cœurs et un SSD divise ces temps par 2 à 3 — et 20 humains ne cliquent pas en
boucle sans pause.

---

## 2. Prérequis du serveur

| Élément | Minimum | Recommandé |
|---|---|---|
| Processeur | 2 cœurs | 4 cœurs |
| Mémoire | 4 Go | 8 Go |
| Disque | **SSD**, 20 Go libres | SSD + 2ᵉ disque/clé USB pour les sauvegardes |
| Système | Windows 10/11, Windows Server, Ubuntu 22.04+ | — |
| Réseau | IP **fixe** sur le réseau local (ex. `192.168.1.10`) | — |
| Logiciel | **Python 3.11 ou 3.12** (« Add python.exe to PATH » coché) | — |

> ⚠️ Le fichier de base doit être sur un **disque local** du serveur. Jamais sur
> un partage réseau (SMB/NFS) ni dans un dossier synchronisé (OneDrive, Drive).

Linux uniquement — bibliothèques pour la génération PDF :
`sudo apt install libpango-1.0-0 libpangocairo-1.0-0 libcairo2 libgdk-pixbuf-2.0-0`

---

## 3. Installation (10 minutes)

1. Copier le dossier du projet sur le serveur, par ex. `C:\YELEN\yelen-school`
   (ou `git clone https://github.com/nayxuspro-sketch/yelen-school.git`).
2. Double-cliquer **`demarrer-autonome.bat`** (Linux : `./demarrer-autonome.sh`).
   Le script, au premier lancement :
   - crée `.env` à partir de `.env.autonome.example` et génère la `SECRET_KEY` ;
   - crée l'environnement Python et installe les dépendances (une seule fois) ;
   - crée la base `data/yelen_school.sqlite3`, applique les migrations, crée la
     table de cache et le compte administrateur ;
   - démarre le serveur web et ouvre le navigateur.
3. Ouvrir `.env` et renseigner l'IP fixe du serveur :
   ```ini
   ALLOWED_HOSTS=localhost,127.0.0.1,192.168.1.10,serveur-ecole
   CSRF_TRUSTED_ORIGINS=http://localhost:8000,http://192.168.1.10:8000,http://serveur-ecole:8000
   ```
   puis relancer le script.
4. **Pare-feu Windows** : autoriser le port **8000 TCP en entrée**
   (Pare-feu → Paramètres avancés → Règles de trafic entrant → Nouvelle règle → Port).
5. Sur un poste client : `http://192.168.1.10:8000` → page de connexion.
6. Se connecter avec le compte administrateur, changer son mot de passe, puis
   passer `ENSURE_ADMIN=false` dans `.env`.

---

## 4. Variables `.env` propres au mode autonome

| Variable | Valeur | Rôle |
|---|---|---|
| `DB_ENGINE` | `sqlite` | Active le mode autonome (`postgresql` = mode serveur/Docker) |
| `SQLITE_PATH` | chemin absolu (facultatif) | Emplacement du fichier de base (défaut `data/yelen_school.sqlite3`) |
| `CACHE_BACKEND` | `database` (défaut en SQLite) | Cache partagé entre workers sans Redis (`file`, `locmem`, `redis` possibles) |
| `DISABLE_HTTPS_REDIRECT` | `true` | Réseau local sans certificat |
| `PORT` | `8000` | Port d'écoute |
| `WEB_THREADS` / `WEB_WORKERS` | `8` / `4` | Parallélisme du serveur web |
| `BACKUP_DIR`, `BACKUP_KEEP` | dossier, `30` | Sauvegardes automatiques |

Ce que l'application applique automatiquement en mode SQLite
(`core/db_sqlite.py`) : `journal_mode=WAL` (lectures jamais bloquées par les
écritures), `synchronous=NORMAL`, `busy_timeout=30 s`, `foreign_keys=ON`, cache
de 64 Mo par connexion, `mmap` 256 Mo.

---

## 5. Sauvegardes (indispensable)

La commande suivante réalise une **sauvegarde à chaud** (l'application peut
rester utilisée), vérifie l'intégrité de la copie, la compresse et conserve
les `BACKUP_KEEP` dernières :

```bat
.venv\Scripts\python manage.py sauvegarde_sqlite
.venv\Scripts\python manage.py sauvegarde_sqlite --dest E:\Sauvegardes --garder 60
```

> ❌ Ne **copiez pas** le fichier `.sqlite3` à la main pendant que le serveur
> tourne : en mode WAL, une partie des données récentes est dans le fichier
> `-wal` et la copie serait incohérente. Utilisez la commande ci-dessus.

**Planification Windows** : Planificateur de tâches → Créer une tâche de base →
Quotidien 22 h → Démarrer un programme :
`C:\YELEN\yelen-school\.venv\Scripts\python.exe` avec les arguments
`manage.py sauvegarde_sqlite` et « Commencer dans » `C:\YELEN\yelen-school`.

**Restauration** : arrêter le serveur, décompresser la sauvegarde `.gz`, la
renommer `yelen_school.sqlite3` à la place du fichier actuel, redémarrer.

---

## 6. Démarrage automatique avec Windows

Option simple : placer un raccourci vers `demarrer-autonome.bat` dans
`shell:startup` (session ouverte automatiquement). Option robuste : créer un
service avec **NSSM** (`nssm install YelenSchool`) pointant sur
`.venv\Scripts\waitress-serve.exe` avec les arguments
`--listen=0.0.0.0:8000 --threads=8 yelen_school.wsgi:application`.

---

## 7. Passer de SQLite à PostgreSQL (si l'établissement grandit)

Au-delà de ~50 utilisateurs réellement simultanés ou pour un serveur central
multi-établissements, migrer vers PostgreSQL :

```bash
# 1. Export depuis SQLite
DB_ENGINE=sqlite python manage.py dumpdata --natural-foreign --natural-primary \
    --exclude contenttypes --exclude auth.permission --exclude sessions \
    --exclude admin.logentry -o export.json
# 2. Import dans PostgreSQL (après .env en mode postgresql + migrate)
python manage.py migrate
python manage.py loaddata export.json
```

---

## 8. Dépannage

| Symptôme | Cause probable | Solution |
|---|---|---|
| `DisallowedHost` / erreur 400 sur les postes | IP du serveur absente de `ALLOWED_HOSTS` | Compléter `.env`, redémarrer |
| Erreur CSRF (403) à la connexion depuis un poste | Origine absente de `CSRF_TRUSTED_ORIGINS` | Ajouter `http://IP:8000` |
| Postes qui n'atteignent pas la page | Pare-feu du serveur | Ouvrir le port 8000 TCP |
| `database is locked` | Fichier sur un partage réseau / dossier synchronisé, ou 2 serveurs sur le même fichier | Disque local, un seul serveur |
| Lenteur générale | Disque mécanique, antivirus qui scanne `data/` | SSD ; exclure `data\` de l'analyse en temps réel |
| Fichier `-wal` volumineux | Serveur jamais redémarré, checkpoint en attente | Normal jusqu'à quelques dizaines de Mo ; se résorbe seul |

---

## 9. Fichiers ajoutés par le mode autonome

| Fichier | Rôle |
|---|---|
| `.env.autonome.example` | Modèle de configuration du mode autonome |
| `demarrer-autonome.bat` / `.sh` | Installation + démarrage sans Docker |
| `core/db_sqlite.py` | PRAGMA SQLite (WAL…) appliqués à chaque connexion |
| `core/management/commands/sauvegarde_sqlite.py` | Sauvegarde à chaud avec rotation |
| `etablissements/migrations/0005_…` + `_compat.py` | Champ `cycles` portable (ArrayField → JSONField) |
| `scripts/seed_charge.py` | Jeu de données réaliste (1 500 élèves × 5 ans) pour tests |
| `scripts/charge_20_navigateurs.py` | Test de charge de bout en bout (20 navigateurs simulés) |
