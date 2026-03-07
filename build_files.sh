#!/bin/sh
# Vercel build script — runs after @vercel/python installs requirements.txt
set -e

echo "==> Running migrations (SQLite)"
VERCEL= python manage.py migrate --noinput

echo "==> Collecting static files"
python manage.py collectstatic --noinput -v 0 2>/dev/null || true

echo "==> Build complete"
