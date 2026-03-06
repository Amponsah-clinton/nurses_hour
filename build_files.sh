#!/bin/sh
# Vercel build: install deps, run migrations (db in project dir), optional collectstatic.
# Use sh for portability; avoid bash-specific syntax.

set -e

PYTHON=python
PIP=pip
command -v python3 >/dev/null 2>&1 && PYTHON=python3
command -v pip3 >/dev/null 2>&1 && PIP=pip3

echo "==> Installing dependencies"
"$PIP" install -r requirements.txt -q 2>/dev/null || "$PYTHON" -m pip install -r requirements.txt -q

echo "==> Running migrations (db in project dir for bundle)"
# DATABASE_PATH so settings.py writes db.sqlite3 here; included in deployment.
export DATABASE_PATH="$(pwd)/db.sqlite3"
"$PYTHON" manage.py migrate --noinput

echo "==> Collecting static files (optional)"
"$PYTHON" manage.py collectstatic --noinput --clear -v 0 2>/dev/null || true

echo "==> Build complete"
