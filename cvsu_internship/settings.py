"""
Django settings for cvsu_internship project.
"""

import os
from pathlib import Path

# ---------------------------------------
# Configuration Helper for Render Compatibility
# ---------------------------------------
def get_config(key, default='', cast_func=None):
    """
    Universal config getter that works everywhere.
    
    Priority:
    1. System environment variables (Render/Heroku/Docker)
    2. .env file via python-decouple (local development)
    3. Default value
    """
    # 1. First check system environment (Render production)
    value = os.environ.get(key)
    
    # 2. If not in system env, try .env file (local development)
    if value is None:
        try:
            from decouple import config as decouple_config
            # Use decouple's config with casting if needed
            if cast_func:
                value = decouple_config(key, default=default, cast=cast_func)
            else:
                value = decouple_config(key, default=default)
        except:
            value = default
    
    # 3. Apply casting for booleans, integers, etc.
    if cast_func and value is not None and value != '':
        if cast_func == bool:
            # Handle string booleans
            if isinstance(value, str):
                value = value.lower() in ('true', 'yes', '1', 't', 'y')
            return value
        else:
            try:
                return cast_func(value)
            except (ValueError, TypeError):
                return default
    
    return value

# Import decouple for any remaining direct usage
from decouple import config

BASE_DIR = Path(__file__).resolve().parent.parent

# ---------------------------------------
# Basic Deployment Settings
# ---------------------------------------
SECRET_KEY = get_config('DJANGO_SECRET_KEY', default='')
DEBUG = get_config('DJANGO_DEBUG', default=False, cast_func=bool)
ALLOWED_HOSTS = get_config('DJANGO_ALLOWED_HOSTS', default='localhost').split(',')

CSRF_TRUSTED_ORIGINS = [
    'https://cvsu-internship-matching.onrender.com',
]

# ---------------------------------------
# Database (PostgreSQL)
# ---------------------------------------
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': get_config('POSTGRES_DB', default='cvsu_internship'),
        'USER': get_config('POSTGRES_USER', default='postgres'),
        'PASSWORD': get_config('POSTGRES_PASSWORD', default='postgres'),
        'HOST': get_config('POSTGRES_HOST', default='localhost'),
        'PORT': get_config('POSTGRES_PORT', default='5432'),
    }
}

ROOT_URLCONF = 'cvsu_internship.urls'

# ---------------------------------------
# Templates
# ---------------------------------------
TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [os.path.join(BASE_DIR, 'templates')],
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

# ---------------------------------------
# Password Validators
# ---------------------------------------
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# ---------------------------------------
# Internationalization
# ---------------------------------------
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'Asia/Manila'
USE_I18N = True
USE_TZ = True

# ---------------------------------------
# Static Files (Render + WhiteNoise FIXED)
# ---------------------------------------
STATIC_URL = 'static/'
STATICFILES_DIRS = [os.path.join(BASE_DIR, 'static')]
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')

# WhiteNoise for static file serving
STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"
WHITENOISE_SKIP_COMPRESS_EXTENSIONS = ['.jpg', '.jpeg', '.png', '.gif', '.webp', '.svg', 'ico']

# ---------------------------------------
# Media Files (Need cloud storage for prod)
# ---------------------------------------
MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')

# ---------------------------------------
# Middleware (WhiteNoise Added)
# ---------------------------------------
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',  # REQUIRED for static files on Render
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'allauth.account.middleware.AccountMiddleware',
]

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# ---------------------------------------
# Crispy Forms
# ---------------------------------------
CRISPY_ALLOWED_TEMPLATE_PACKS = "bootstrap5"
CRISPY_TEMPLATE_PACK = "bootstrap5"

# ---------------------------------------
# Authentication
# ---------------------------------------
AUTH_USER_MODEL = 'accounts.User'

AUTHENTICATION_BACKENDS = [
    'django.contrib.auth.backends.ModelBackend',
    'allauth.account.auth_backends.AuthenticationBackend',
]

SITE_ID = 1

# AllAuth settings
ACCOUNT_EMAIL_REQUIRED = True
ACCOUNT_EMAIL_VERIFICATION = 'mandatory'
ACCOUNT_AUTHENTICATION_METHOD = 'username_email'
ACCOUNT_USERNAME_REQUIRED = True
ACCOUNT_LOGOUT_ON_GET = True
ACCOUNT_EMAIL_DOMAIN_WHITELIST = ["cvsu.edu.ph"]
ACCOUNT_UNIQUE_EMAIL = True
ACCOUNT_EMAIL_CONFIRMATION_EXPIRE_DAYS = 3
ACCOUNT_EMAIL_SUBJECT_PREFIX = '[CVSU Internship Matching] '
ACCOUNT_EMAIL_CONFIRMATION_HMAC = True
ACCOUNT_ADAPTER = 'accounts.adapters.CustomAccountAdapter'

LOGIN_REDIRECT_URL = 'dashboard:home'
LOGOUT_REDIRECT_URL = 'home'
LOGIN_URL = 'account_login'

# ---------------------------------------
# Email Settings (SendGrid with Fallbacks)
# ---------------------------------------
# Get all email-related configs
SENDGRID_API_KEY = get_config('SENDGRID_API_KEY', default='')
SENDGRID_SANDBOX_MODE = get_config('SENDGRID_SANDBOX_MODE_IN_DEBUG', default=True, cast_func=bool)
EMAIL_BACKEND_CONFIG = get_config('EMAIL_BACKEND', default='')

# Determine the backend to use
if EMAIL_BACKEND_CONFIG:
    # Use explicitly configured backend
    EMAIL_BACKEND = EMAIL_BACKEND_CONFIG
elif DEBUG and SENDGRID_SANDBOX_MODE:
    # Local development with sandbox mode
    EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
else:
    # Production - always SMTP
    EMAIL_BACKEND = 'sendgrid_backend.SendgridBackend'

# SMTP Configuration (for when using SMTP)
EMAIL_HOST = get_config('EMAIL_HOST', default='smtp.sendgrid.net')
EMAIL_HOST_USER = get_config('EMAIL_HOST_USER', default='apikey')

# IMPORTANT: For SendGrid, password is the API key
if SENDGRID_API_KEY:
    EMAIL_HOST_PASSWORD = SENDGRID_API_KEY
else:
    # Fallback to old EMAIL_HOST_PASSWORD if SENDGRID_API_KEY not set
    EMAIL_HOST_PASSWORD = get_config('EMAIL_HOST_PASSWORD', default='')

EMAIL_PORT = get_config('EMAIL_PORT', default=587, cast_func=int)
EMAIL_USE_TLS = get_config('EMAIL_USE_TLS', default=True, cast_func=bool)
DEFAULT_FROM_EMAIL = get_config('DEFAULT_FROM_EMAIL', default='internmatchingcvsu@gmail.com')

# Email timeout settings (important for Render)
EMAIL_TIMEOUT = 30  # seconds

# ---------------------------------------
# Channels (WebSockets)
# ---------------------------------------
CHANNEL_LAYERS = {
    'default': {
        'BACKEND': 'channels_redis.core.RedisChannelLayer',
        'CONFIG': {
            'hosts': [(get_config('REDIS_URL', default='rediss://localhost:6379'))],
        },
    },
}

# ---------------------------------------
# CORS
# ---------------------------------------
CORS_ALLOW_ALL_ORIGINS = False
cors_origins = get_config('CORS_ALLOWED_ORIGINS', default='')
CORS_ALLOWED_ORIGINS = cors_origins.split(',') if cors_origins else []

# ---------------------------------------
# Installed Apps
# ---------------------------------------
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.sites',

    # Third-party
    'cloudinary_storage',
    'cloudinary',
    'rest_framework',
    'crispy_forms',
    'crispy_bootstrap5',
    'allauth',
    'allauth.account',
    'allauth.socialaccount',
    'channels',
    'corsheaders',
    'django_filters',
    'widget_tweaks',

    # Local apps
    'accounts',
    'internship',
    'chat',
    'dashboard',
]

# ---------------------------------------
# Cloudinary Settings
# ---------------------------------------
CLOUDINARY_STORAGE = {
    'CLOUD_NAME': get_config('CLOUDINARY_CLOUD_NAME', default=''),
    'API_KEY': get_config('CLOUDINARY_API_KEY', default=''),
    'API_SECRET': get_config('CLOUDINARY_API_SECRET', default=''),
}

# Only use Cloudinary if all credentials are present
if all([CLOUDINARY_STORAGE['CLOUD_NAME'], 
         CLOUDINARY_STORAGE['API_KEY'], 
         CLOUDINARY_STORAGE['API_SECRET']]):
    DEFAULT_FILE_STORAGE = 'cloudinary_storage.storage.MediaCloudinaryStorage'
    
    # Also configure Cloudinary SDK directly
    import cloudinary
    cloudinary.config(
        cloud_name=CLOUDINARY_STORAGE['CLOUD_NAME'],
        api_key=CLOUDINARY_STORAGE['API_KEY'],
        api_secret=CLOUDINARY_STORAGE['API_SECRET'],
    )
else:
    # Fallback to local storage
    DEFAULT_FILE_STORAGE = 'django.core.files.storage.FileSystemStorage'


# ---------------------------------------
# Base URL for Production (Added for OnlyOffice)
# ---------------------------------------
BASE_URL = get_config('BASE_URL', default='https://cvsu-internship-matching.onrender.com')

# ---------------------------------------
# CORS Configuration (Expanded)
# ---------------------------------------
CORS_ALLOW_ALL_ORIGINS = False
cors_origins = get_config('CORS_ALLOWED_ORIGINS', default='')
CORS_ALLOWED_ORIGINS = [origin.strip() for origin in cors_origins.split(',')] if cors_origins else []

# Additional CORS settings for OnlyOffice
CORS_ALLOW_CREDENTIALS = True
CORS_ALLOW_METHODS = [
    'DELETE',
    'GET',
    'OPTIONS',
    'PATCH',
    'POST',
    'PUT',
]
CORS_ALLOW_HEADERS = [
    'accept',
    'accept-encoding',
    'authorization',
    'content-type',
    'dnt',
    'origin',
    'user-agent',
    'x-csrftoken',
    'x-requested-with',
]

# Update CSRF trusted origins dynamically
csrf_trusted = get_config('CSRF_TRUSTED_ORIGINS', default='')
if csrf_trusted:
    CSRF_TRUSTED_ORIGINS = [origin.strip() for origin in csrf_trusted.split(',')]
else:
    CSRF_TRUSTED_ORIGINS = [
        'https://cvsu-internship-matching.onrender.com',
        'http://139.59.96.100',  # Your Digital Ocean droplet
    ]


# ---------------------------------------
# OnlyOffice Settings
# ---------------------------------------
ONLYOFFICE_URL = get_config('ONLYOFFICE_URL', default='http://localhost/')
# Ensure no trailing slash for API loading
if ONLYOFFICE_URL.endswith('/'):
    ONLYOFFICE_URL = ONLYOFFICE_URL.rstrip('/')
    
ONLYOFFICE_SECRET = get_config('ONLYOFFICE_SECRET', default='your-local-secret')

# Helper function to get absolute file URLs
def get_absolute_media_url(relative_url):
    """Convert relative media URL to absolute URL for OnlyOffice"""
    if not relative_url:
        return ""
    
    # If already absolute (Cloudinary)
    if relative_url.startswith('http'):
        return relative_url
    
    # For production
    if not DEBUG:
        return f"{BASE_URL}{relative_url}"
    
    # For local development
    return relative_url

# ---------------------------------------
# Debug Output for Configuration Verification
# ---------------------------------------
if DEBUG:
    print("\n" + "="*60)
    print("CONFIGURATION VERIFICATION (DEBUG MODE)")
    print("="*60)
    print(f"Running on: {'RENDER' if 'RENDER' in os.environ else 'LOCAL'}")
    print(f"SECRET_KEY loaded: {'YES' if SECRET_KEY else 'NO'}")
    print(f"DEBUG mode: {DEBUG}")
    print(f"SENDGRID_API_KEY loaded: {'YES' if SENDGRID_API_KEY else 'NO'}")
    print(f"CLOUDINARY_CLOUD_NAME loaded: {'YES' if get_config('CLOUDINARY_CLOUD_NAME') else 'NO'}")
    print(f"ONLYOFFICE_URL: {ONLYOFFICE_URL}")
    print(f"Email Backend: {EMAIL_BACKEND}")
    print(f"Email Host: {EMAIL_HOST}")
    print(f"Email From: {DEFAULT_FROM_EMAIL}")
    print("="*60)
