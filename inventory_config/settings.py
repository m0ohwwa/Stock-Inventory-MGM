"""
Django settings for inventory_config project.
"""

from pathlib import Path
import os
from dotenv import load_dotenv

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# Load environment variables from .env file (must be in project root)
load_dotenv(BASE_DIR / '.env')

try:
    from decouple import config
except ImportError:
    def config(key, default=None, cast=None):
        val = os.getenv(key)
        if val is None or val == '':
            return default
        if cast is bool:
            return str(val).lower() in ('true', '1', 'yes', 'on')
        if cast is int:
            return int(val)
        if callable(cast):
            return cast(val)
        return val

SECRET_KEY = os.getenv('SECRET_KEY', 'django-insecure-g#qih*+ti#+pwkgfsz4%&p%!w#qd3jrp-g6bw-qfth+oqk&%rl')

DEBUG = True

ALLOWED_HOSTS = ['*']

# Application definition
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'inventory.apps.InventoryConfig',
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

ROOT_URLCONF = 'inventory_config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'django.template.context_processors.media',
                'inventory.context_processors.currency_settings',
            ],
        },
    },
]

WSGI_APPLICATION = 'inventory_config.wsgi.application'

# Database Setup (SQLite by default for zero-setup execution, MySQL settings included below)
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

# Optional MySQL Configuration (Uncomment and edit credentials to switch to MySQL):
"""
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': 'inventory_db',
        'USER': 'root',
        'PASSWORD': 'yourpassword',
        'HOST': 'localhost',
        'PORT': '3306',
    }
}
"""

AUTHENTICATION_BACKENDS = [
    'inventory.backends.EmailOrUsernameModelBackend',
    'django.contrib.auth.backends.ModelBackend',
]

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
]

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

# Static & Media Files
STATIC_URL = '/static/'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATIC_ROOT = BASE_DIR / 'staticfiles'

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# Authentication URLs
LOGIN_URL = 'login'
LOGIN_REDIRECT_URL = 'dashboard'
LOGOUT_REDIRECT_URL = 'login'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# ──────────────────────────────────────────────────────────────
# Email Configuration — loaded from .env via config()
# ──────────────────────────────────────────────────────────────
EMAIL_BACKEND    = config('EMAIL_BACKEND', default='django.core.mail.backends.smtp.EmailBackend')
EMAIL_HOST       = config('EMAIL_HOST', default='smtp.gmail.com')
EMAIL_PORT       = config('EMAIL_PORT', default=587, cast=int)
EMAIL_HOST_USER  = config('EMAIL_HOST_USER', default='').strip()
_raw_pwd         = config('EMAIL_HOST_PASSWORD', default='').strip().strip('"').strip("'")
EMAIL_HOST_PASSWORD = ''.join(_raw_pwd.split())
EMAIL_USE_TLS    = config('EMAIL_USE_TLS', default=True, cast=bool)
DEFAULT_FROM_EMAIL = config('DEFAULT_FROM_EMAIL', default=EMAIL_HOST_USER)
