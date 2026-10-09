# YELEN SCHOOL

Système de gestion scolaire pour établissements privés du Burkina Faso.

## Stack

| Composant | Technologie |
|-----------|-------------|
| Backend | Django 5.2 |
| Base de données | PostgreSQL 15 |
| Cache / Files | Redis |
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

## Déploiement

Voir [`docs/GUIDE_DEPLOIEMENT_WINDOWS.md`](docs/GUIDE_DEPLOIEMENT_WINDOWS.md) pour les instructions complètes.

## Licence

Usage interne — Établissements YELEN SCHOOL.
