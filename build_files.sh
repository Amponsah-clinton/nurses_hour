#!/bin/bash
# Run at Vercel build time to pre-migrate the SQLite database into the deployment bundle.
set -e

echo "==> Installing dependencies"
pip install -r requirements.txt --quiet

echo "==> Running migrations"
python manage.py migrate --noinput

echo "==> Collecting static files"
python manage.py collectstatic --noinput --clear 2>/dev/null || true

echo "==> Build complete"
