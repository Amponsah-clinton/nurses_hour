"""
Django settings for publishing_company project.
"""

from pathlib import Path
import os
from dotenv import load_dotenv

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# Load environment variables from .env file
load_dotenv(BASE_DIR / '.env')

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.getenv('SECRET_KEY', 'django-insecure-change-this-in-production')

# SECURITY WARNING: don't run with debug turned on in production!
# Controlled via DEBUG env var. Locally you can keep DEBUG=True in .env.
# On Vercel, set DEBUG=False in the dashboard so production uses proper static handling.
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

SESSION_COOKIE_SECURE = False
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = 'Lax'
# Use signed-cookie sessions (no DB table needed; works on Vercel and locally)
SESSION_ENGINE = 'django.contrib.sessions.backends.signed_cookies'
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

# Database — SQLite for Django auth/sessions.
# On Vercel the build step runs migrate and writes db.sqlite3 into /var/task (read-only bundle).
# For writes (signup, etc.) we use /tmp/db.sqlite3 at runtime; it is pre-seeded by copying the
# built db at cold start (see wsgi.py). App data always goes through Supabase REST API.
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': '/tmp/db.sqlite3' if os.getenv('VERCEL') else BASE_DIR / 'db.sqlite3',
    }
}

# Supabase Configuration
# IMPORTANT: Set these as environment variables in production!
# Get keys from: https://supabase.com/dashboard → Settings → API
SUPABASE_URL = os.getenv('SUPABASE_URL', 'https://plyqzvmtkdymnaxvipyu.supabase.co')
SUPABASE_KEY = os.getenv('SUPABASE_KEY', 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InBseXF6dm10a2R5bW5heHZpcHl1Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzIzOTMzMjAsImV4cCI6MjA4Nzk2OTMyMH0.26zvvdZa9x1ZOKtfDZfjXACmtMv3ssOsEXjc7P_qxAM')  # anon/public key
SUPABASE_SERVICE_KEY = os.getenv('SUPABASE_SERVICE_KEY', 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InBseXF6dm10a2R5bW5heHZpcHl1Iiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc3MjM5MzMyMCwiZXhwIjoyMDg3OTY5MzIwfQ.zhnP7XYrw5xslOQtkp1oeaGmUci4HsEdyysKjjbZSyU')  # service_role key (bypasses RLS)
SUPABASE_STORAGE_BUCKET = os.getenv('SUPABASE_STORAGE_BUCKET', 'project-files')
# Bucket for case study file uploads (create it in Supabase Dashboard → Storage: name = case-studies, public)
SUPABASE_STORAGE_BUCKET_CASE_STUDIES = os.getenv('SUPABASE_STORAGE_BUCKET_CASE_STUDIES', 'case-studies')
# Bucket for books/slides file uploads (create it in Supabase Dashboard → Storage: name = book-slide, public)
SUPABASE_STORAGE_BUCKET_BOOKS_SLIDES = os.getenv('SUPABASE_STORAGE_BUCKET_BOOKS_SLIDES', 'book-slide')
# Sync signup/data to Supabase REST API (requires app_users table - see supabase_app_users.sql)
SUPABASE_SYNC_ENABLED = True

# Validate Supabase configuration on startup
_key_len = len(SUPABASE_KEY or '')
_svc_len = len(SUPABASE_SERVICE_KEY or '')
if not SUPABASE_URL or not SUPABASE_KEY or not SUPABASE_SERVICE_KEY:
    print("\n" + "=" * 80)
    print("WARNING: Supabase configuration is incomplete!")
    print("=" * 80)
    print("SUPABASE_URL:", "OK" if SUPABASE_URL else "MISSING")
    print("SUPABASE_KEY:", "OK" if _key_len > 100 else "MISSING or INVALID (length: {})".format(_key_len))
    print("SUPABASE_SERVICE_KEY:", "OK" if _svc_len > 100 else "MISSING or INVALID (length: {})".format(_svc_len))
    print("\nTo fix: set SUPABASE_KEY and SUPABASE_SERVICE_KEY in .env or as environment variables.")
    print("=" * 80 + "\n")
elif _key_len > 100 and _svc_len > 100:
    print("[Supabase Config] OK - Connected to {} (anon: {} chars, service: {} chars)".format(
        SUPABASE_URL, _key_len, _svc_len))
else:
    print("[Supabase Config] WARNING - Keys may be invalid (anon: {} chars, service: {} chars)".format(
        _key_len, _svc_len))

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


PAYSTACK_SECRET_KEY ="sk_test_7c773f96c11b14401a005855684ed93ac9042154"
PAYSTACK_PUBLIC_KEY ="pk_test_81ab70cdc3b06eecabcfac2b3f32ca03f1ecb4ee"
