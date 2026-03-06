#!/bin/sh
# Vercel build script — runs after @vercel/python installs requirements.txt
set -e

echo "==> Running migrations"
if [ -n "$DATABASE_URL" ]; then
    # Supabase Postgres or any DATABASE_URL: migrate against it directly
    echo "    Using DATABASE_URL (Postgres)"
    python manage.py migrate --noinput
else
    # SQLite fallback: write db.sqlite3 into project dir so it ships in the bundle.
    # Unset VERCEL so settings.py uses BASE_DIR/db.sqlite3 instead of /tmp.
    echo "    Using SQLite (no DATABASE_URL)"
    DATABASE_PATH="$(pwd)/db.sqlite3" VERCEL= python manage.py migrate --noinput
fi

echo "==> Collecting static files"
python manage.py collectstatic --noinput -v 0 2>/dev/null || true

echo "==> Build complete"
