#!/usr/bin/env bash
# Installation locale YELEN SCHOOL pour Linux/macOS.
# PostgreSQL et Redis sont gérés localement par Docker.

set -Eeuo pipefail

ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
COMPOSE_FILE="$ROOT/docker-compose.client.yml"
ENV_FILE="$ROOT/.env"

fail() {
    echo "[ERREUR] $1" >&2
    exit 1
}

require_command() {
    command -v "$1" >/dev/null 2>&1 || fail "$1 est introuvable."
}

get_env_value() {
    local key="$1"
    sed -n -E "s/^${key}=(.*)$/\1/p" "$ENV_FILE" | head -n 1
}

set_env_value() {
    local key="$1"
    local value="$2"
    local escaped_value
    escaped_value="$(printf '%s' "$value" | sed 's/[&|]/\\&/g')"

    if grep -qE "^${key}=" "$ENV_FILE"; then
        sed -i.bak -E "s|^${key}=.*$|${key}=${escaped_value}|" "$ENV_FILE"
    else
        printf '%s\n' "${key}=${value}" >> "$ENV_FILE"
    fi
    rm -f "${ENV_FILE}.bak"
}

ensure_env_value() {
    local key="$1"
    local value="$2"
    local current
    current="$(get_env_value "$key" || true)"
    if [[ -z "$current" || "$current" =~ generer|choisissez|votre-|changez ]]; then
        set_env_value "$key" "$value"
    fi
}

ensure_env_list_values() {
    local key="$1"
    shift
    local current
    local required
    current="$(get_env_value "$key" || true)"
    if [[ -z "$current" || "$current" =~ generer|choisissez|votre-|changez ]]; then
        current=''
    fi
    for required in "$@"; do
        case ",$current," in
            *",$required,"*) ;;
            *) current="${current:+$current,}$required" ;;
        esac
    done
    set_env_value "$key" "$current"
}

random_hex() {
    if command -v openssl >/dev/null 2>&1; then
        openssl rand -hex 32
    else
        od -An -N32 -tx1 /dev/urandom | tr -d ' \n'
    fi
}

require_command docker
[[ -f "$COMPOSE_FILE" ]] || fail "Fichier introuvable : $COMPOSE_FILE"

docker info >/dev/null 2>&1 || fail 'Docker ne fonctionne pas. Démarrez Docker puis relancez le script.'

fresh_installation=0
if [[ ! -f "$ENV_FILE" ]]; then
    [[ -f "$ROOT/.env.example" ]] || fail '.env.example est introuvable.'
    cp "$ROOT/.env.example" "$ENV_FILE"
    fresh_installation=1
    echo '[OK] Fichier .env créé à partir de .env.example'
fi

http_port="$(get_env_value YELEN_HTTP_PORT || true)"
http_port="${http_port:-8000}"
if ! [[ "$http_port" =~ ^[0-9]{1,5}$ ]] || (( 10#$http_port < 1 || 10#$http_port > 65535 )); then
    fail 'YELEN_HTTP_PORT doit être un port compris entre 1 et 65535.'
fi
LOGIN_URL="http://localhost:${http_port}/accounts/login/"

secret_key="$(random_hex)$(random_hex)"
db_password="Yelen-$(random_hex | cut -c1-24)"
sms_webhook_token="$(random_hex)$(random_hex)"
initial_admin_password="$(random_hex | cut -c1-32)"
lan_ip="$(ip -4 route get 1.1.1.1 2>/dev/null | awk '{for (i = 1; i <= NF; i++) if ($i == "src") {print $(i + 1); exit}}' || true)"
if [[ -z "$lan_ip" || "$lan_ip" == 127.* || "$lan_ip" == 169.254.* ]]; then
    lan_ip="$(hostname -I 2>/dev/null | tr ' ' '\n' | grep -Ev '^(127\.|169\.254\.)' | head -n 1 || true)"
fi
if [[ -z "$lan_ip" ]]; then
    lan_ip="127.0.0.1"
fi

ensure_env_value SECRET_KEY "$secret_key"
if [[ "$fresh_installation" -eq 1 ]]; then
    ensure_env_value DB_PASSWORD "$db_password"
else
    existing_db_password="$(get_env_value DB_PASSWORD || true)"
    if [[ -z "$existing_db_password" || "$existing_db_password" =~ generer|choisissez|votre-|changez ]]; then
        fail 'DB_PASSWORD doit être configuré dans .env avant de réutiliser une base existante.'
    fi
fi
ensure_env_value DB_NAME 'yelen_school_db'
ensure_env_value DB_USER 'yelen_user'
ensure_env_value SMS_WEBHOOK_TOKEN "$sms_webhook_token"
ensure_env_value DEBUG 'False'
ensure_env_value DISABLE_HTTPS_REDIRECT 'true'
ensure_env_list_values ALLOWED_HOSTS \
    'localhost' \
    '127.0.0.1' \
    "$lan_ip"
ensure_env_list_values CSRF_TRUSTED_ORIGINS \
    'http://localhost' \
    'http://127.0.0.1' \
    "http://localhost:${http_port}" \
    "http://127.0.0.1:${http_port}" \
    "http://${lan_ip}:${http_port}"
if [[ "$fresh_installation" -eq 1 ]]; then
    set_env_value ENSURE_ADMIN true
    set_env_value INITIAL_ADMIN_PASSWORD "$initial_admin_password"
    set_env_value EMAIL_HOST ''
fi

echo '[OK] Configuration locale préparée'

docker compose -f "$COMPOSE_FILE" up -d --build

echo '[1/2] Attente de la page de connexion...'
ready=0
for _ in $(seq 1 60); do
    if curl -fsS -o /dev/null "$LOGIN_URL"; then
        ready=1
        break
    fi
    sleep 2
done

if [[ "$ready" -ne 1 ]]; then
    docker compose -f "$COMPOSE_FILE" logs --tail=80 web || true
    fail 'Le serveur ne répond pas après 120 secondes.'
fi

if [[ "$fresh_installation" -eq 1 ]]; then
    set_env_value ENSURE_ADMIN false
    # Le secret n'est plus nécessaire après la création du compte et ne doit
    # pas rester dans .env. Le compte impose son remplacement à la connexion.
    set_env_value INITIAL_ADMIN_PASSWORD ''
fi

echo '[OK] YELEN SCHOOL est opérationnel'
echo "Adresse : $LOGIN_URL"
if [[ "$fresh_installation" -eq 1 ]]; then
    echo 'Compte initial : admin@yelen.edu'
    echo "Mot de passe temporaire à usage unique : $initial_admin_password"
    echo 'Le remplacement de ce mot de passe est obligatoire à la première connexion.'
fi
echo "Accès réseau local : http://${lan_ip}:${http_port}/"

if command -v xdg-open >/dev/null 2>&1; then
    xdg-open "$LOGIN_URL" >/dev/null 2>&1 || true
elif command -v open >/dev/null 2>&1; then
    open "$LOGIN_URL" >/dev/null 2>&1 || true
fi
