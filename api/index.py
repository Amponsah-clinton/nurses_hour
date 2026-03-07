"""
Vercel entry point — same pattern as xceldata. All routes go through Django WSGI.
Uses SQLite in /tmp on Vercel; Supabase (env SUPABASE_URL, SUPABASE_SERVICE_KEY) for auth and data.
"""
import os

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'publishing_company.settings')

if os.getenv('VERCEL'):
    # Copy build-time db.sqlite3 to /tmp so tables exist (build_files.sh runs migrate with SQLite)
    import shutil
    _bundle_db = os.path.join(os.path.dirname(__file__), '..', 'db.sqlite3')
    _runtime_db = '/tmp/db.sqlite3'
    if os.path.isfile(_bundle_db) and not os.path.isfile(_runtime_db):
        try:
            shutil.copy2(_bundle_db, _runtime_db)
        except Exception:
            pass

from django.core.wsgi import get_wsgi_application
app = get_wsgi_application()
