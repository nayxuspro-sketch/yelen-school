#!/usr/bin/env bash
# ============================================================================
#  YELEN SCHOOL — Démarrage du serveur en MODE AUTONOME (SQLite, sans Docker)
#  Linux / macOS.  Windows : utiliser demarrer-autonome.bat
# ============================================================================
set -euo pipefail
cd "$(dirname "$0")"

echo "============================================================"
echo "  YELEN SCHOOL - Démarrage du serveur (mode autonome SQLite)"
echo "============================================================"

# 1. Python
PY=$(command -v python3 || command -v python || true)
[ -z "$PY" ] && { echo "[ERREUR] Python 3.11+ introuvable."; exit 1; }
echo "[OK] $($PY --version)"

# 2. .env
if [ ! -f .env ]; then
    cp .env.autonome.example .env
    KEY=$($PY -c 'import secrets;print(secrets.token_urlsafe(64))')
    sed -i.bak "s|SECRET_KEY=CHANGEZ-MOI.*|SECRET_KEY=$KEY|" .env && rm -f .env.bak
    echo "[OK] .env créé (clé secrète générée). Renseignez ALLOWED_HOSTS / CSRF_TRUSTED_ORIGINS avec l'IP du serveur."
fi

# 3. venv + dépendances (WeasyPrint a besoin de Pango/Cairo : apt install libpango-1.0-0 libpangocairo-1.0-0 libcairo2)
if [ ! -x .venv/bin/python ]; then
    echo "[1/5] Création de l'environnement Python…"
    $PY -m venv .venv
fi
# shellcheck disable=SC1091
source .venv/bin/activate
if [ ! -f .venv/.deps_ok ]; then
    echo "[2/5] Installation des dépendances (une seule fois)…"
    pip install --upgrade pip -q
    pip install -r requirements/base.txt -q
    touch .venv/.deps_ok
else
    echo "[2/5] Dépendances déjà installées"
fi

# 4. Base, cache, statiques, admin
export DB_ENGINE=sqlite
set -a; source .env; set +a
echo "[3/5] Mise à jour de la base de données…"
python manage.py migrate --noinput
python manage.py createcachetable >/dev/null 2>&1 || true
echo "[4/5] Fichiers statiques…"
python manage.py collectstatic --noinput >/dev/null 2>&1
[ "${ENSURE_ADMIN:-false}" = "true" ] && python manage.py ensure_admin

# 5. Serveur web (Gunicorn)
PORT="${PORT:-8000}"
WORKERS="${WEB_WORKERS:-4}"
LANIP=$(hostname -I 2>/dev/null | awk '{print $1}' || echo "IP-DU-SERVEUR")
echo "[5/5] Démarrage du serveur web…"
echo
echo "============================================================"
echo "  Serveur prêt. Accès depuis les postes de l'école :"
echo
echo "      http://$LANIP:$PORT"
echo
echo "  Pare-feu : autoriser le port $PORT/tcp en entrée. Ctrl+C pour arrêter."
echo "============================================================"
exec gunicorn yelen_school.wsgi:application \
    --bind "0.0.0.0:$PORT" --workers "$WORKERS" --threads 2 --timeout 120 \
    --access-logfile data/access.log --error-logfile -
