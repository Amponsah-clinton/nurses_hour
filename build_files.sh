#!/bin/bash
# Run at Vercel build time to pre-migrate the SQLite database into the deployment bundle.
set -e

echo "==> Installing dependencies"
pip install -r requirements.txt --quiet

echo "==> Running migrations (create db in project dir so it is included in bundle)"
# Unset VERCEL so Django uses BASE_DIR/db.sqlite3; /tmp is not in the deployment bundle.
VERCEL= python manage.py migrate --noinput

echo "==> Collecting static files"
python manage.py collectstatic --noinput --clear 2>/dev/null || true

echo "==> Build complete"
