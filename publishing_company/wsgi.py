"""
WSGI config for publishing_company project.

On Vercel, the build step runs `python manage.py migrate` which writes a fully-migrated
db.sqlite3 into the deployment bundle at /var/task/db.sqlite3.
At cold start we copy that pre-migrated file to /tmp/db.sqlite3 so the runtime SQLite
database already has all tables — no migrations needed per-request.
"""

import os
import shutil

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'publishing_company.settings')

if os.getenv('VERCEL'):
    # /var/task is the read-only deployment bundle; /tmp is writable per-instance.
    _bundle_db = '/var/task/db.sqlite3'
    _runtime_db = '/tmp/db.sqlite3'
    if not os.path.exists(_runtime_db) and os.path.exists(_bundle_db):
        shutil.copy2(_bundle_db, _runtime_db)

from django.core.wsgi import get_wsgi_application  # noqa: E402

application = get_wsgi_application()
