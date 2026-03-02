"""
Django settings for publishing_company project.
"""

from pathlib import Path
import os
import dj_database_url
from dotenv import load_dotenv

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# Load environment variables from .env file
load_dotenv(BASE_DIR / '.env')

# Quick-start development settings - unsuitable for production
# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.getenv('SECRET_KEY', 'django-insecure-change-this-in-production')

# SECURITY WARNING: don't run with debug turned on in production!
# Controlled via environment so Vercel can run with DEBUG=False.
DEBUG = os.getenv('DEBUG', 'False').lower() == 'true'

ALLOWED_HOSTS = ['*', 'localhost', '127.0.0.1' , '.vercel.app']

# CSRF and Security Settings for Production
CSRF_TRUSTED_ORIGINS = [
    'https://scholarindexing.academicdigital.space',
    'https://*.academicdigital.space',
    'http://scholarindexing.academicdigital.space',
    'http://*.academicdigital.space',
    'https://doi.academicdigital.space',
    'http://doi.academicdigital.space',
    'https://nurseshour.vercel.app',
    'http://nurseshour.vercel.app',
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
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

# WhiteNoise for static files in production only
if not DEBUG:
    MIDDLEWARE.insert(1, 'whitenoise.middleware.WhiteNoiseMiddleware')

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

# Database
# Priority:
# 1. If DATABASE_URL is set, use it (Postgres/MySQL/etc.).
# 2. Else if running on Vercel (VERCEL env var), use a writable SQLite DB in /tmp.
# 3. Else (local dev), use SQLite in BASE_DIR.
DATABASE_URL = os.getenv('DATABASE_URL')

if DATABASE_URL:
    DATABASES = {
        'default': dj_database_url.config(
            default=DATABASE_URL,
            conn_max_age=600,
            conn_health_checks=True,
        )
    }
elif os.getenv('VERCEL'):
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': '/tmp/db.sqlite3',
        }
    }
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }

# Supabase Configuration (combining SQLite + Supabase)
# Publishable: sb_publishable_QKXVNEfSSVpi_RWpIqOG9w__Bosa_pH
# Secret: sb_secret_PNFsLO7U2y-qR1q85vbdIA__NMpj_ef
SUPABASE_URL = os.getenv('SUPABASE_URL', 'https://plyqzvmtdkymnaxvpiyu.supabase.co')
SUPABASE_KEY = os.getenv('SUPABASE_KEY', 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InBseXF6dm10a2R5bW5heHZpcHl1Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzIzOTMzMjAsImV4cCI6MjA4Nzk2OTMyMH0.26zvvdZa9x1ZOKtfDZfjXACmtMv3ssOsEXjc7P_qxAM')
SUPABASE_SERVICE_KEY = os.getenv('SUPABASE_SERVICE_KEY', 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InBseXF6dm10a2R5bW5heHZpcHl1Iiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc3MjM5MzMyMCwiZXhwIjoyMDg3OTY5MzIwfQ.zhnP7XYrw5xslOQtkp1oeaGmUci4HsEdyysKjjbZSyU')
SUPABASE_STORAGE_BUCKET = os.getenv('SUPABASE_STORAGE_BUCKET', 'project-files')

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

if not DEBUG:
    STATICFILES_STORAGE = 'whitenoise.storage.CompressedStaticFilesStorage'
else:
    STATICFILES_STORAGE = 'django.contrib.staticfiles.storage.StaticFilesStorage'

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

# Auth redirects (for @login_required and similar)
LOGIN_URL = '/login/'
LOGIN_REDIRECT_URL = '/dashboard/'
LOGOUT_REDIRECT_URL = '/'

# Hardcoded admin (dashboard access)
ADMIN_EMAIL = 'amoasamoahransford17@gmail.com'
ADMIN_INITIAL_PASSWORD = 'Nursehub2026@'

# Notify this email when a new contact/inquiry is submitted
INQUIRY_NOTIFY_EMAIL = os.getenv('INQUIRY_NOTIFY_EMAIL', 'amoasamoahransford17@gmail.com')
