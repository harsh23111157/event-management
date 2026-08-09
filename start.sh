#!/bin/bash

export DJANGO_SETTINGS_MODULE=config.settings.production

echo "--- Running migrations ---"
python manage.py migrate --noinput

echo "--- Seeding demo users and data ---"
python manage.py seed_demo_data || echo "WARNING: seed_demo_data had errors, continuing..."

echo "--- Collecting static files ---"
python manage.py collectstatic --noinput || echo "WARNING: collectstatic had errors, continuing..."

echo "--- Starting gunicorn on port ${PORT:-8000} ---"
exec gunicorn config.wsgi:application \
    --bind "0.0.0.0:${PORT:-8000}" \
    --workers 2 \
    --timeout 120 \
    --log-level info \
    --access-logfile - \
    --error-logfile -
