#!/bin/sh
# Vercel build script — runs after @vercel/python installs requirements.txt
set -e

echo "==> Running migrations"
# Postgres if DATABASE_URL is set OR individual DB_* vars are set (matches settings.py)
if [ -n "$DATABASE_URL" ] && [ "${DATABASE_URL#*projectid}" = "$DATABASE_URL" ]; then
    echo "    Using DATABASE_URL (Postgres)"
    python manage.py migrate --noinput
elif [ -n "$DB_HOST" ] && [ -n "$DB_USER" ] && [ -n "$DB_PASSWORD" ]; then
    echo "    Using DB_* vars (Postgres)"
    python manage.py migrate --noinput
else
    # SQLite fallback: write db.sqlite3 into project dir so it ships in the bundle.
    echo "    Using SQLite"
    DATABASE_PATH="$(pwd)/db.sqlite3" VERCEL= python manage.py migrate --noinput
fi

echo "==> Collecting static files"
python manage.py collectstatic --noinput -v 0 2>/dev/null || true

echo "==> Build complete"
