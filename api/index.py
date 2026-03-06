"""
Vercel entry point. All routes go through Django WSGI.
On Vercel without a Postgres DATABASE_URL, copies the pre-migrated SQLite bundle
to writable /tmp so Django auth tables exist on cold start.
"""
import os
import shutil

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'publishing_company.settings')

# Only copy SQLite if no Postgres DATABASE_URL configured
if os.getenv('VERCEL') and not os.getenv('DATABASE_URL'):
    _bundle_db = '/var/task/db.sqlite3'
    _runtime_db = '/tmp/db.sqlite3'
    if not os.path.exists(_runtime_db) and os.path.exists(_bundle_db):
        shutil.copy2(_bundle_db, _runtime_db)

from django.core.wsgi import get_wsgi_application  # noqa: E402

app = get_wsgi_application()
