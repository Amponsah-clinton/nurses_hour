"""
Django settings for publishing_company project.
Uses SQLite for Django (sessions, auth) and Supabase for app data/storage.
"""
from pathlib import Path
import os
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / '.env')


WSGI_APPLICATION = 'website.wsgi.app'

SECRET_KEY = os.getenv('SECRET_KEY', 'django-insecure-change-this-in-production')
DEBUG = os.getenv('DEBUG', 'True') == 'True'
ALLOWED_HOSTS = ['*', 'localhost', '127.0.0.1', '.vercel.app']

# CSRF and Security Settings
CSRF_TRUSTED_ORIGINS = [
    'https://nurseshour.vercel.app',
    'http://nurseshour.vercel.app',
    'https://nurses-hour.vercel.app',
    'http://nurses-hour.vercel.app',
    'http://127.0.0.1:8000',
    'http://localhost:8000',
]
CSRF_COOKIE_SECURE = False
CSRF_COOKIE_HTTPONLY = False
CSRF_COOKIE_SAMESITE = 'Lax'
CSRF_USE_SESSIONS = False

# Use signed cookie sessions on Vercel — SQLite in /tmp is ephemeral per serverless instance
SESSION_ENGINE = 'django.contrib.sessions.backends.signed_cookies'
SESSION_COOKIE_SECURE = False
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = 'Lax'
SESSION_SAVE_EVERY_REQUEST = True

# Application definition
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'website',
    'whitenoise',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'publishing_company.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'publishing_company.wsgi.application'

# Database - SQLite for Django (sessions, auth, etc.)
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': '/tmp/db.sqlite3' if os.getenv('VERCEL') else BASE_DIR / 'db.sqlite3',
    }
}

# Supabase: anon (publishable) and service_role (secret) keys from your project
SUPABASE_URL = os.getenv('SUPABASE_URL', 'https://plyqzvmtkdymnaxvipyu.supabase.co')
SUPABASE_KEY = os.getenv('SUPABASE_KEY', 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InBseXF6dm10a2R5bW5heHZpcHl1Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzIzOTMzMjAsImV4cCI6MjA4Nzk2OTMyMH0.26zvvdZa9x1ZOKtfDZfjXACmtMv3ssOsEXjc7P_qxAM')
SUPABASE_SERVICE_KEY = os.getenv('SUPABASE_SERVICE_KEY', 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InBseXF6dm10a2R5bW5heHZpcHl1Iiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc3MjM5MzMyMCwiZXhwIjoyMDg3OTY5MzIwfQ.zhnP7XYrw5xslOQtkp1oeaGmUci4HsEdyysKjjbZSyU')
SUPABASE_STORAGE_BUCKET = os.getenv('SUPABASE_STORAGE_BUCKET', 'project-files')
SUPABASE_STORAGE_BUCKET_CASE_STUDIES = os.getenv('SUPABASE_STORAGE_BUCKET_CASE_STUDIES', 'case-studies')
SUPABASE_STORAGE_BUCKET_BOOKS_SLIDES = os.getenv('SUPABASE_STORAGE_BUCKET_BOOKS_SLIDES', 'book-slide')
SUPABASE_SYNC_ENABLED = True

if SUPABASE_URL and SUPABASE_KEY and SUPABASE_SERVICE_KEY:
    if len(SUPABASE_KEY) > 100 and len(SUPABASE_SERVICE_KEY) > 100:
        print(f"[Supabase Config] OK - Connected to {SUPABASE_URL}")
    else:
        print("[Supabase Config] WARNING - Keys may be invalid")
else:
    print("[Supabase Config] WARNING - Configuration incomplete!")

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# Internationalization
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

# Static files (css/, js/, img/ at project root)
STATIC_URL = '/static/'
STATICFILES_DIRS = [
    BASE_DIR,
]
STATIC_ROOT = BASE_DIR / 'staticfiles'
# WhiteNoise: serve compressed static files and also use finders so we don't need collectstatic on Vercel
STATICFILES_STORAGE = 'whitenoise.storage.CompressedStaticFilesStorage'
WHITENOISE_USE_FINDERS = True

# Media files
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# Email Configuration
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_USE_TLS = True
EMAIL_HOST = os.getenv('EMAIL_HOST', 'smtp.gmail.com')
EMAIL_PORT = int(os.getenv('EMAIL_PORT', '587'))
EMAIL_HOST_USER = os.getenv('EMAIL_HOST_USER', '')
EMAIL_HOST_PASSWORD = os.getenv('EMAIL_HOST_PASSWORD', '')
DEFAULT_FROM_EMAIL = EMAIL_HOST_USER or 'noreply@example.com'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Auth redirects
LOGIN_URL = '/login/'
LOGIN_REDIRECT_URL = '/dashboard/'
LOGOUT_REDIRECT_URL = '/'

# Hardcoded admin (dashboard access)
ADMIN_EMAIL = 'amoasamoahransford17@gmail.com'
ADMIN_INITIAL_PASSWORD = 'Nursehub2026@'

# Notify this email when a new contact/inquiry is submitted
INQUIRY_NOTIFY_EMAIL = os.getenv('INQUIRY_NOTIFY_EMAIL', 'amoasamoahransford17@gmail.com')


# Paystack
PAYSTACK_SECRET_KEY = os.getenv('PAYSTACK_SECRET_KEY', '')
PAYSTACK_PUBLIC_KEY = os.getenv('PAYSTACK_PUBLIC_KEY', '')

# DataHub Ghana — data bundle delivery API & wallet top-up
DATAHUB_API_KEY = os.getenv('DATAHUB_API_KEY', '')
DATAHUB_BASE_URL = os.getenv('DATAHUB_BASE_URL', 'https://app.datahubgh.com/api/external')
DATAHUB_TOPUP_URL = os.getenv('DATAHUB_TOPUP_URL', 'https://app.datahubgh.com')
DATAHUB_BUNDLES_URL = os.getenv('DATAHUB_BUNDLES_URL', '')
DATAHUB_BUNDLES_BASE = os.getenv('DATAHUB_BUNDLES_BASE', 'https://app.datahubgh.com/api')

# Optional: allow dashboard (e.g. buy_data) access via Authorization: Bearer <secret>
DASHBOARD_API_SECRET = os.getenv('DASHBOARD_API_SECRET', '')
