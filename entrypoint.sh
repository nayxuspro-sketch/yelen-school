#!/bin/bash
set -e

python manage.py migrate --noinput
python manage.py collectstatic --noinput --clear

if [ "$ENSURE_ADMIN" = "true" ]; then
    python manage.py ensure_admin
fi

exec "$@"
