#!/usr/bin/env bash
# Restauration PostgreSQL de l'installation locale YELEN SCHOOL.
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

if [[ "${2:-}" != '--yes' ]]; then
    echo 'ATTENTION : cette opération remplace toutes les données de la base.'
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

echo '[1/3] Suppression de la base actuelle...'
docker compose -f "$COMPOSE_FILE" exec -T db dropdb --if-exists -U "$DB_USER" "$DB_NAME"
docker compose -f "$COMPOSE_FILE" exec -T db createdb -U "$DB_USER" -O "$DB_USER" "$DB_NAME"

echo '[2/3] Restauration de la sauvegarde...'
if ! cat "$BACKUP_FILE" | docker compose -f "$COMPOSE_FILE" exec -T db \
    pg_restore -U "$DB_USER" -d "$DB_NAME" --no-owner --no-privileges --exit-on-error -; then
    fail 'La restauration PostgreSQL a échoué. La base doit être restaurée depuis une autre sauvegarde valide.'
fi

echo '[3/3] Redémarrage de YELEN SCHOOL et application des migrations...'
docker compose -f "$COMPOSE_FILE" up -d web >/dev/null

echo '[OK] Restauration terminée.'
echo 'Vérifiez la connexion et quelques données importantes dans l’application.'
