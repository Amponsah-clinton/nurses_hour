"""
Vercel entry point. All routes go through Django WSGI.

On Vercel you must set Supabase Postgres: DATABASE_URL or DB_HOST + DB_USER + DB_PASSWORD.
See Supabase Dashboard → Settings → Database → Connection string (Transaction, port 6543).
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
    if not _using_postgres():
        print("[api/index.py] No Postgres config: set DATABASE_URL or DB_HOST, DB_USER, DB_PASSWORD in Vercel env.", file=sys.stderr)
    if _using_postgres():
        try:
            import django
            django.setup()
            from django.core.management import call_command
            call_command('migrate', '--noinput', verbosity=0)
        except Exception as _mig_err:
            import traceback
            print("[api/index.py] migrate failed (check DB credentials):", file=sys.stderr)
            traceback.print_exc(file=sys.stderr)

# Load Django WSGI app; on failure Vercel logs will show the traceback
try:
    from django.core.wsgi import get_wsgi_application  # noqa: E402
    app = get_wsgi_application()
except Exception as e:
    import traceback
    print("[api/index.py] Failed to load Django app (often missing/wrong DATABASE_URL or DB_*):", file=sys.stderr)
    traceback.print_exc(file=sys.stderr)
    raise
