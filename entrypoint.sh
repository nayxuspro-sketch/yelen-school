#!/bin/bash
set -e

python manage.py migrate --noinput
python manage.py collectstatic --noinput --clear
python manage.py ensure_admin

exec "$@"
