#!/bin/sh
# Production start script (Railway / any Linux server).
# Collects static files, applies migrations and starts Gunicorn.
set -e
python manage.py collectstatic --noinput
python manage.py migrate --noinput
python manage.py prepare_site
exec gunicorn config.wsgi:application \
  --bind "0.0.0.0:${PORT:-8000}" \
  --workers "${WEB_CONCURRENCY:-3}" \
  --timeout 60 \
  --access-logfile - \
  --error-logfile -
