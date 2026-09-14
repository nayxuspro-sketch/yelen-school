#!/usr/bin/env bash
# Sauvegarde PostgreSQL de l'installation locale YELEN SCHOOL.

set -Eeuo pipefail

ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
COMPOSE_FILE="$ROOT/docker-compose.client.yml"
ENV_FILE="$ROOT/.env"
BACKUP_DIR="${BACKUP_DIR:-$ROOT/backups}"
KEEP="${KEEP:-30}"

fail() {
    echo "[ERREUR] $1" >&2
    exit 1
}

get_env_value() {
    local key="$1"
    sed -n -E "s/^${key}=(.*)$/\1/p" "$ENV_FILE" | head -n 1
}

command -v docker >/dev/null 2>&1 || fail 'Docker est introuvable.'
[[ -f "$COMPOSE_FILE" ]] || fail "Fichier introuvable : $COMPOSE_FILE"
[[ -f "$ENV_FILE" ]] || fail '.env est introuvable. Lancez d’abord l’installation locale.'
docker info >/dev/null 2>&1 || fail 'Docker ne fonctionne pas.'

DB_NAME="$(get_env_value DB_NAME)"
DB_USER="$(get_env_value DB_USER)"
DB_NAME="${DB_NAME:-yelen_school_db}"
DB_USER="${DB_USER:-yelen_user}"

if ! [[ "$KEEP" =~ ^[1-9][0-9]*$ ]]; then
    fail 'KEEP doit être un nombre entier supérieur à zéro.'
fi

mkdir -p "$BACKUP_DIR"
timestamp="$(date '+%Y%m%d_%H%M%S')"
backup_file="$BACKUP_DIR/yelen_school_${timestamp}.dump"
temporary_file="${backup_file}.part"
trap 'rm -f "$temporary_file"' EXIT

echo "[1/2] Export de PostgreSQL vers $backup_file"
if ! docker compose -f "$COMPOSE_FILE" exec -T db \
    pg_dump -U "$DB_USER" -d "$DB_NAME" --format=custom > "$temporary_file"; then
    fail 'La sauvegarde PostgreSQL a échoué.'
fi

if [[ ! -s "$temporary_file" ]]; then
    fail 'Le fichier de sauvegarde est vide.'
fi
mv "$temporary_file" "$backup_file"

old_files="$(ls -1t "$BACKUP_DIR"/yelen_school_*.dump 2>/dev/null || true)"
count=0
while IFS= read -r old_file; do
    [[ -z "$old_file" ]] && continue
    count=$((count + 1))
    if (( count > KEEP )); then
        rm -f -- "$old_file"
    fi
done <<< "$old_files"

echo "[2/2] Sauvegarde terminée : $backup_file"
echo "Rétention appliquée : $KEEP sauvegarde(s) maximum"
