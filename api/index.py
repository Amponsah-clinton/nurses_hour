"""
Vercel entry point. All routes go through Django WSGI.

Cold-start behaviour:
- Postgres in use (DATABASE_URL or DB_HOST+DB_USER+DB_PASSWORD): run `migrate --noinput`
  so Django tables exist. Idempotent — already-applied migrations are skipped.
- SQLite fallback: copy pre-migrated db.sqlite3 from bundle to /tmp.
"""
import os
import sys

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'publishing_company.settings')

def _using_postgres():
    if os.getenv('DATABASE_URL', '').strip() and 'projectid' not in os.getenv('DATABASE_URL', ''):
        return True
    return bool(
        os.getenv('DB_HOST') and os.getenv('DB_USER') and os.getenv('DB_PASSWORD')
    )

if os.getenv('VERCEL'):
    if _using_postgres():
        # Postgres — run migrations so Django tables exist.
        try:
            import django
            django.setup()
            from django.core.management import call_command
            call_command('migrate', '--noinput', verbosity=0)
        except Exception as _mig_err:
            print(f"[api/index.py] migrate failed: {_mig_err}", file=sys.stderr)
    else:
        # SQLite fallback — copy pre-migrated bundle db to writable /tmp.
        import shutil
        _bundle_db = '/var/task/db.sqlite3'
        _runtime_db = '/tmp/db.sqlite3'
        if not os.path.exists(_runtime_db) and os.path.exists(_bundle_db):
            shutil.copy2(_bundle_db, _runtime_db)

# Load Django WSGI app; on failure print full traceback to stderr so Vercel logs show the real error
try:
    from django.core.wsgi import get_wsgi_application  # noqa: E402
    app = get_wsgi_application()
except Exception as e:
    import traceback
    print("[api/index.py] Failed to load Django app:", file=sys.stderr)
    traceback.print_exc(file=sys.stderr)
    raise
