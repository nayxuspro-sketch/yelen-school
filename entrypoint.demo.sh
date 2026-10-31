#!/bin/bash
# Point d'entrée de l'instance de démonstration (offre hébergée, chantier B8).
#
# Même image que l'installation d'école (Dockerfile), un comportement différent : au premier démarrage sur
# une base vide, le jeu de démonstration est chargé ; les fois suivantes, les données existantes sont
# conservées. La remise à zéro périodique est faite par `python manage.py reinitialiser_demo`
# (voir docker-compose.demo.yml, service `reset`).
set -e

python manage.py migrate --noinput
python manage.py createcachetable 2>/dev/null || true
python manage.py collectstatic --noinput --clear

# Base vierge (premier démarrage ou volume recréé) : chargement du jeu de démonstration.
if ! python manage.py shell -c "from etablissements.models import Etablissement; raise SystemExit(0 if Etablissement.objects.exists() else 1)"; then
    echo "[DEMO] Base vide : chargement du jeu de démonstration."
    python manage.py reinitialiser_demo
fi

exec "$@"
