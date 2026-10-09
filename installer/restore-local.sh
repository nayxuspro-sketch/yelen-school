#!/usr/bin/env bash
# Restauration PostgreSQL et médias de l'installation locale YELEN SCHOOL.
# Usage : ./installer/restore-local.sh backups/yelen_school_YYYYMMDD_HHMMSS.dump

set -Eeuo pipefail

ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
COMPOSE_FILE="$ROOT/docker-compose.client.yml"
ENV_FILE="$ROOT/.env"
BACKUP_FILE="${1:-}"

fail() {
    echo "[ERREUR] $1" >&2
    exit 1
}

get_env_value() {
    local key="$1"
    sed -n -E "s/^${key}=(.*)$/\1/p" "$ENV_FILE" | head -n 1
}

if [[ -z "$BACKUP_FILE" ]]; then
    echo 'Usage : ./installer/restore-local.sh chemin/vers/sauvegarde.dump' >&2
    exit 2
fi

[[ -f "$BACKUP_FILE" ]] || fail "Sauvegarde introuvable : $BACKUP_FILE"
command -v docker >/dev/null 2>&1 || fail 'Docker est introuvable.'
[[ -f "$COMPOSE_FILE" ]] || fail "Fichier introuvable : $COMPOSE_FILE"
[[ -f "$ENV_FILE" ]] || fail '.env est introuvable.'
docker info >/dev/null 2>&1 || fail 'Docker ne fonctionne pas.'

DB_NAME="$(get_env_value DB_NAME)"
DB_USER="$(get_env_value DB_USER)"
DB_NAME="${DB_NAME:-yelen_school_db}"
DB_USER="${DB_USER:-yelen_user}"
MEDIA_BACKUP_FILE="${BACKUP_FILE%.dump}_media.tar.gz"

if [[ "${2:-}" != '--yes' ]]; then
    echo 'ATTENTION : cette opération remplace toutes les données de la base et des médias.'
    read -r -p 'Tapez RESTAURER pour continuer : ' confirmation
    [[ "$confirmation" == 'RESTAURER' ]] || fail 'Restauration annulée.'
fi

# Le serveur web est arrêté afin d'éviter toute connexion pendant la
# reconstruction de la base. Il sera relancé même en cas d'échec.
docker compose -f "$COMPOSE_FILE" stop web >/dev/null
restart_web() {
    docker compose -f "$COMPOSE_FILE" up -d web >/dev/null 2>&1 || true
}
trap restart_web EXIT

echo '[1/5] Suppression de la base actuelle...'
docker compose -f "$COMPOSE_FILE" exec -T db dropdb --if-exists -U "$DB_USER" "$DB_NAME"
docker compose -f "$COMPOSE_FILE" exec -T db createdb -U "$DB_USER" -O "$DB_USER" "$DB_NAME"

echo '[2/5] Restauration de la base PostgreSQL...'
if ! cat "$BACKUP_FILE" | docker compose -f "$COMPOSE_FILE" exec -T db \
    pg_restore -U "$DB_USER" -d "$DB_NAME" --no-owner --no-privileges --exit-on-error -; then
    fail 'La restauration PostgreSQL a échoué. La base doit être restaurée depuis une autre sauvegarde valide.'
fi

echo '[3/5] Redémarrage du service web...'
docker compose -f "$COMPOSE_FILE" up -d web >/dev/null

if [[ -f "$MEDIA_BACKUP_FILE" ]]; then
    echo '[4/5] Restauration des médias...'
    if ! cat "$MEDIA_BACKUP_FILE" | docker compose -f "$COMPOSE_FILE" exec -T web \
        python /app/installer/media_archive.py restore; then
        fail 'La restauration des médias a échoué.'
    fi
else
    echo "[AVERTISSEMENT] Archive médias absente : $MEDIA_BACKUP_FILE"
    echo 'La base est restaurée, mais les fichiers téléversés ne le sont pas.'
fi

echo '[5/5] Contrôle fonctionnel post-restauration...'
docker compose -f "$COMPOSE_FILE" exec -T web python manage.py check
health_ok=0
for _ in $(seq 1 30); do
    if docker compose -f "$COMPOSE_FILE" exec -T web python -c \
        "import json,urllib.request; d=json.load(urllib.request.urlopen('http://127.0.0.1:8000/health/', timeout=5)); assert d.get('status') == 'ok' and d.get('database') == 'ok' and d.get('cache') == 'ok'" \
        >/dev/null 2>&1; then
        health_ok=1
        break
    fi
    sleep 2
done
if [[ "$health_ok" -ne 1 ]]; then
    fail 'Le contrôle /health/ a échoué après la restauration.'
fi

echo '[OK] Restauration terminée et contrôle /health/ réussi.'
echo 'Vérifiez aussi la connexion et quelques données importantes dans l’application.'
