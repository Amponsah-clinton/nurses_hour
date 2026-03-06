"""
WSGI config for publishing_company project.
On Vercel, this module is imported on each cold start. We use that moment
to ensure the SQLite database in /tmp has all migrations applied so that
tables like website_userprofile exist before handling requests.
"""

import os

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'publishing_company.settings')

from django.core.wsgi import get_wsgi_application  # noqa: E402

# On Vercel, run migrations against the /tmp SQLite DB at cold start.
if os.getenv('VERCEL'):
    try:
        import django  # noqa: E402

        django.setup()
        from django.core.management import call_command  # noqa: E402

        # Apply migrations quietly; if this fails we still proceed so the
        # app can return a friendly error instead of crashing import-time.
        call_command('migrate', interactive=False, run_syncdb=True, verbosity=0)
    except Exception:
        # Failing silently here avoids breaking cold start entirely;
        # individual views (like home) are already defensive about missing tables.
        pass

application = get_wsgi_application()
