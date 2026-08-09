#!/bin/bash
set -e

export DJANGO_SETTINGS_MODULE=config.settings.production

echo "==> Running migrations..."
python manage.py migrate --noinput

echo "==> Collecting static files..."
python manage.py collectstatic --noinput --clear

echo "==> Starting gunicorn..."
exec gunicorn config.wsgi:application \
    --bind "0.0.0.0:${PORT:-8000}" \
    --workers 2 \
    --timeout 120 \
    --log-level info \
    --access-logfile -
