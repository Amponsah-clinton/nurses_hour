"""
Vercel entry point. All routes go through Django WSGI.

Cold-start behaviour:
- DATABASE_URL set (Supabase Postgres): run `migrate --noinput` once so tables exist.
  Django's migration framework is idempotent — already-applied migrations are skipped instantly.
- No DATABASE_URL (SQLite fallback): copy pre-migrated db.sqlite3 from bundle to /tmp.
"""
import os

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'publishing_company.settings')

if os.getenv('VERCEL'):
    database_url = os.getenv('DATABASE_URL')
    if database_url:
        # Postgres (Supabase) — run migrations so Django tables exist.
        # This is fast after the first deploy since nothing will be pending.
        try:
            import django
            django.setup()
            from django.core.management import call_command
            call_command('migrate', '--noinput', verbosity=0)
        except Exception as _mig_err:
            import sys
            print(f"[api/index.py] migrate failed: {_mig_err}", file=sys.stderr)
    else:
        # SQLite fallback — copy pre-migrated bundle db to writable /tmp.
        import shutil
        _bundle_db = '/var/task/db.sqlite3'
        _runtime_db = '/tmp/db.sqlite3'
        if not os.path.exists(_runtime_db) and os.path.exists(_bundle_db):
            shutil.copy2(_bundle_db, _runtime_db)

from django.core.wsgi import get_wsgi_application  # noqa: E402

app = get_wsgi_application()
