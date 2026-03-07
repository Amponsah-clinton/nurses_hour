"""
Vercel entry point. All routes go through Django WSGI.
SQLite only; database in /tmp on Vercel.
"""
import os
import sys

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'publishing_company.settings')

if os.getenv('VERCEL'):
    # Ensure /tmp/db.sqlite3 exists: copy from build bundle or run migrate
    _runtime_db = '/tmp/db.sqlite3'
    _bundle_db = os.path.normpath(os.path.join(os.path.dirname(__file__), '..', 'db.sqlite3'))
    if os.path.isfile(_bundle_db) and not os.path.isfile(_runtime_db):
        try:
            import shutil
            shutil.copy2(_bundle_db, _runtime_db)
        except Exception:
            pass
    if not os.path.isfile(_runtime_db):
        try:
            import django
            django.setup()
            from django.core.management import call_command
            call_command('migrate', '--noinput', verbosity=0)
        except Exception as e:
            sys.stderr.write(f"[api/index.py] migrate (create DB): {e!r}\n")

try:
    from django.core.wsgi import get_wsgi_application
    app = get_wsgi_application()
except Exception as e:
    import traceback
    sys.stderr.write("[api/index.py] Failed to load Django app:\n")
    traceback.print_exc(file=sys.stderr)
    raise
