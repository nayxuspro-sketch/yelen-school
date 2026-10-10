# YELEN SCHOOL

Système de gestion scolaire pour établissements privés du Burkina Faso.

## Stack

| Composant | Technologie |
|-----------|-------------|
| Backend | Django 5.2 |
| Base de données | PostgreSQL 15 (mode serveur) ou SQLite (mode autonome) |
| Cache / Files | Redis (mode serveur) ou cache base de données (mode autonome) |
| PDF | WeasyPrint |
| UI dynamique | HTMX |

## Démarrage rapide (Docker)

```bash
# Cloner le projet
git clone https://github.com/nayxuspro-sketch/yelen-school.git
cd yelen-school

# Copier et configurer l'environnement
cp .env.example .env
# Éditer .env avec vos paramètres

# Lancer les services
docker compose -f docker-compose.dev.yml up --build
```

Accès : `https://localhost`

## Démarrage rapide (mode autonome — sans Docker)

Pour un serveur d'école auquel les postes accèdent par navigateur, sans PostgreSQL ni Redis :

```bat
demarrer-autonome.bat        :: Windows
./demarrer-autonome.sh       #  Linux / macOS
```

La base est un fichier SQLite (`data/yelen_school.sqlite3`), sélectionné par `DB_ENGINE=sqlite` dans `.env`.
Voir [`docs/GUIDE_MODE_AUTONOME_SQLITE.md`](docs/GUIDE_MODE_AUTONOME_SQLITE.md).

## Déploiement

- Mode serveur (Docker, PostgreSQL, Redis) : [`docs/GUIDE_DEPLOIEMENT_WINDOWS.md`](docs/GUIDE_DEPLOIEMENT_WINDOWS.md)
- Mode autonome (SQLite) : [`docs/GUIDE_MODE_AUTONOME_SQLITE.md`](docs/GUIDE_MODE_AUTONOME_SQLITE.md)

## Développement et tests

```bash
pip install -r requirements/dev.txt      # base.txt (exécution) + pytest, model-bakery, coverage…
python manage.py collectstatic --noinput # requis par les tests (manifeste des fichiers statiques)
python -m pytest                         # PostgreSQL par défaut ; SQLite : DB_ENGINE=sqlite CACHE_BACKEND=database
```

`requirements/base.txt` ne contient que les dépendances d'exécution (Docker, mode autonome) ;
les outils de test et de documentation sont dans `requirements/dev.txt`.

## Licence

Usage interne — Établissements YELEN SCHOOL.
