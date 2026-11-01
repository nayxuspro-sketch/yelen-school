#!/usr/bin/env bash
# Programme une sauvegarde quotidienne YELEN SCHOOL via cron.
# Usage : ./installer/register-backup-cron.sh [HH:MM]

set -Eeuo pipefail

ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
SCRIPT="$ROOT/installer/backup-local.sh"
BACKUP_DIR="$ROOT/backups"
LOG_FILE="$BACKUP_DIR/cron.log"
TIME="${1:-22:00}"
MARKER='# YELEN SCHOOL BACKUP'

fail() {
    echo "[ERREUR] $1" >&2
    exit 1
}

shell_quote() {
    # Quote POSIX shell arguments: cron uses /bin/sh, not necessarily Bash.
    local value="$1"
    printf "'%s'" "$(printf '%s' "$value" | sed "s/'/'\\\\''/g")"
}

[[ -x "$SCRIPT" ]] || fail "Script introuvable ou non exécutable : $SCRIPT"
[[ "$TIME" =~ ^([01][0-9]|2[0-3]):[0-5][0-9]$ ]] || fail 'Heure attendue : HH:MM'
command -v crontab >/dev/null 2>&1 || fail 'crontab est introuvable.'
docker_bin="$(command -v docker || true)"
[[ -n "$docker_bin" ]] || fail 'Docker est introuvable. Installez Docker avant de programmer la sauvegarde.'

mkdir -p "$BACKUP_DIR"
hour="${TIME%:*}"
minute="${TIME#*:}"
docker_dir="$(dirname -- "$docker_bin")"
cron_path="$docker_dir:/usr/local/bin:/opt/homebrew/bin:/usr/bin:/bin"
cron_path_quoted="$(shell_quote "$cron_path")"
backup_dir_quoted="$(shell_quote "$BACKUP_DIR")"
script_quoted="$(shell_quote "$SCRIPT")"
log_file_quoted="$(shell_quote "$LOG_FILE")"
cron_line="$minute $hour * * * env PATH=$cron_path_quoted BACKUP_DIR=$backup_dir_quoted $script_quoted >> $log_file_quoted 2>&1 $MARKER"

current="$(crontab -l 2>/dev/null || true)"
filtered="$(printf '%s\n' "$current" | grep -vF "$MARKER" || true)"
{
    printf '%s\n' "$filtered"
    printf '%s\n' "$cron_line"
} | crontab -

echo "[OK] Sauvegarde quotidienne programmée à $TIME."
echo 'Vérifiez la tâche avec : crontab -l'
echo "Journal : $LOG_FILE"
