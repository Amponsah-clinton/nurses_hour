"""
WSGI config for publishing_company project.
"""

import os

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'publishing_company.settings')

from django.core.wsgi import get_wsgi_application  # noqa: E402

application = get_wsgi_application()
