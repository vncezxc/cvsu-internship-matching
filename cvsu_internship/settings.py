"""
Django settings for cvsu_internship project.
"""

import os
import sys
from pathlib import Path
from datetime import timedelta

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

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

# ---------------------------------------
# Security & Deployment Settings
# ---------------------------------------
SECRET_KEY = get_config('DJANGO_SECRET_KEY')
DEBUG = get_config('DJANGO_DEBUG', default=False, cast_func=bool)

# Security settings for production
if not DEBUG:
    SECURE_BROWSER_XSS_FILTER = True
    SECURE_CONTENT_TYPE_NOSNIFF = True
    SECURE_SSL_REDIRECT = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    X_FRAME_OPTIONS = 'DENY'
    SECURE_HSTS_SECONDS = 31536000  # 1 year
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

# Allowed hosts configuration
ALLOWED_HOSTS = get_config('DJANGO_ALLOWED_HOSTS', default='localhost,127.0.0.1').split(',')

# CSRF & CORS configuration
csrf_trusted = get_config('CSRF_TRUSTED_ORIGINS', default='')
if csrf_trusted:
    CSRF_TRUSTED_ORIGINS = [origin.strip() for origin in csrf_trusted.split(',')]
else:
    CSRF_TRUSTED_ORIGINS = [
        'https://cvsu-internship-matching.onrender.com',
        'http://139.59.96.100',
    ]

# Base URL for absolute URLs
BASE_URL = get_config('BASE_URL', default='https://cvsu-internship-matching.onrender.com')

# ---------------------------------------
# Application Definition
# ---------------------------------------
INSTALLED_APPS = [
    # Django core apps
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.sites',
    
    # Third-party apps
    'corsheaders',
    'rest_framework',
    'rest_framework.authtoken',
    'crispy_forms',
    'crispy_bootstrap5',
    'allauth',
    'allauth.account',
    'allauth.socialaccount',
    'channels',
    'django_filters',
    'widget_tweaks',
    'cloudinary_storage',
    'cloudinary',
    'storages',  # For Digital Ocean Spaces/S3
    'django_cleanup.apps.CleanupConfig',  # Auto-delete old files
    
    # Local apps
    'accounts.apps.AccountsConfig',
    'internship.apps.InternshipConfig',
    'chat.apps.ChatConfig',
    'dashboard.apps.DashboardConfig',
]

# ---------------------------------------
# Middleware Configuration
# ---------------------------------------
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'allauth.account.middleware.AccountMiddleware',
]

ROOT_URLCONF = 'cvsu_internship.urls'

# ---------------------------------------
# Database Configuration
# ---------------------------------------
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': get_config('POSTGRES_DB', default='cvsu_internship'),
        'USER': get_config('POSTGRES_USER', default='postgres'),
        'PASSWORD': get_config('POSTGRES_PASSWORD', default='postgres'),
        'HOST': get_config('POSTGRES_HOST', default='localhost'),
        'PORT': get_config('POSTGRES_PORT', default='5432'),
        'CONN_MAX_AGE': 600 if not DEBUG else 0,  # Connection pooling for production
        'OPTIONS': {
            'sslmode': 'require' if not DEBUG else 'prefer',
        }
    }
}

# Use SQLite for local testing if specified
if get_config('USE_SQLITE', default=False, cast_func=bool):
    DATABASES['default'] = {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# ---------------------------------------
# Template Configuration
# ---------------------------------------
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
                'cvsu_internship.context_processors.base_url',  # Custom context processor
            ],
        },
    },
]

# ---------------------------------------
# Password & Authentication
# ---------------------------------------
AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
        'OPTIONS': {
            'max_similarity': 0.7,
        }
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
        'OPTIONS': {
            'min_length': 8,
        }
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

AUTH_USER_MODEL = 'accounts.User'

AUTHENTICATION_BACKENDS = [
    'django.contrib.auth.backends.ModelBackend',
    'allauth.account.auth_backends.AuthenticationBackend',
]

# Password hashing for better security
PASSWORD_HASHERS = [
    'django.contrib.auth.hashers.Argon2PasswordHasher',
    'django.contrib.auth.hashers.PBKDF2PasswordHasher',
    'django.contrib.auth.hashers.PBKDF2SHA1PasswordHasher',
    'django.contrib.auth.hashers.BCryptSHA256PasswordHasher',
]

# ---------------------------------------
# AllAuth Configuration
# ---------------------------------------
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
ACCOUNT_LOGIN_ATTEMPTS_LIMIT = 5
ACCOUNT_LOGIN_ATTEMPTS_TIMEOUT = 300  # 5 minutes
ACCOUNT_SESSION_REMEMBER = True
ACCOUNT_LOGOUT_REDIRECT_URL = 'home'
LOGIN_REDIRECT_URL = 'dashboard:home'
LOGIN_URL = 'account_login'

# ---------------------------------------
# REST Framework Configuration
# ---------------------------------------
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework.authentication.SessionAuthentication',
        'rest_framework.authentication.TokenAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
    'DEFAULT_FILTER_BACKENDS': [
        'django_filters.rest_framework.DjangoFilterBackend',
        'rest_framework.filters.SearchFilter',
        'rest_framework.filters.OrderingFilter',
    ],
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 20,
    'DEFAULT_THROTTLE_CLASSES': [
        'rest_framework.throttling.AnonRateThrottle',
        'rest_framework.throttling.UserRateThrottle',
    ],
    'DEFAULT_THROTTLE_RATES': {
        'anon': '100/day',
        'user': '1000/day',
    }
}

# ---------------------------------------
# CORS Configuration
# ---------------------------------------
CORS_ALLOW_ALL_ORIGINS = False
CORS_ALLOW_CREDENTIALS = True

cors_origins = get_config('CORS_ALLOWED_ORIGINS', default='')
CORS_ALLOWED_ORIGINS = [origin.strip() for origin in cors_origins.split(',')] if cors_origins else []

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

# ---------------------------------------
# Storage Configuration (Digital Ocean Spaces/S3)
# ---------------------------------------
# Storage configuration priority:
# 1. Digital Ocean Spaces (if credentials provided)
# 2. Cloudinary (if credentials provided)
# 3. Local storage (fallback)

# Digital Ocean Spaces Configuration
AWS_ACCESS_KEY_ID = get_config('AWS_ACCESS_KEY_ID', default='')
AWS_SECRET_ACCESS_KEY = get_config('AWS_SECRET_ACCESS_KEY', default='')
AWS_STORAGE_BUCKET_NAME = get_config('AWS_STORAGE_BUCKET_NAME', default='')
AWS_S3_ENDPOINT_URL = get_config('AWS_S3_ENDPOINT_URL', default='https://nyc3.digitaloceanspaces.com')
AWS_S3_REGION_NAME = get_config('AWS_S3_REGION_NAME', default='nyc3')
AWS_S3_CUSTOM_DOMAIN = get_config('AWS_S3_CUSTOM_DOMAIN', default='')

# S3/Spaces settings
AWS_S3_OBJECT_PARAMETERS = {
    'CacheControl': 'max-age=86400',
    'ACL': 'public-read',
}
AWS_LOCATION = 'media'
AWS_DEFAULT_ACL = 'public-read'
AWS_QUERYSTRING_AUTH = False
AWS_S3_FILE_OVERWRITE = False
AWS_S3_SIGNATURE_VERSION = 's3v4'

# Cloudinary Configuration
CLOUDINARY_STORAGE = {
    'CLOUD_NAME': get_config('CLOUDINARY_CLOUD_NAME', default=''),
    'API_KEY': get_config('CLOUDINARY_API_KEY', default=''),
    'API_SECRET': get_config('CLOUDINARY_API_SECRET', default=''),
    'SECURE': True,
    'EXCLUDE_DELETE_ORPHANED_MEDIA_PATHS': ('media/avatars/',),
}

# Determine which storage to use
USE_DIGITAL_OCEAN_SPACES = all([
    AWS_ACCESS_KEY_ID,
    AWS_SECRET_ACCESS_KEY,
    AWS_STORAGE_BUCKET_NAME,
])

USE_CLOUDINARY = all([
    CLOUDINARY_STORAGE['CLOUD_NAME'],
    CLOUDINARY_STORAGE['API_KEY'],
    CLOUDINARY_STORAGE['API_SECRET'],
])

if USE_DIGITAL_OCEAN_SPACES:
    # Use Digital Ocean Spaces
    DEFAULT_FILE_STORAGE = 'storages.backends.s3boto3.S3Boto3Storage'
    AWS_S3_ENDPOINT_URL = AWS_S3_ENDPOINT_URL
    
    # Configure Cloudinary SDK if also available (for possible hybrid use)
    if USE_CLOUDINARY:
        import cloudinary
        cloudinary.config(
            cloud_name=CLOUDINARY_STORAGE['CLOUD_NAME'],
            api_key=CLOUDINARY_STORAGE['API_KEY'],
            api_secret=CLOUDINARY_STORAGE['API_SECRET'],
            secure=True,
        )
    
elif USE_CLOUDINARY:
    # Use Cloudinary
    DEFAULT_FILE_STORAGE = 'cloudinary_storage.storage.MediaCloudinaryStorage'
    
    import cloudinary
    cloudinary.config(
        cloud_name=CLOUDINARY_STORAGE['CLOUD_NAME'],
        api_key=CLOUDINARY_STORAGE['API_KEY'],
        api_secret=CLOUDINARY_STORAGE['API_SECRET'],
        secure=True,
    )
else:
    # Fallback to local storage
    DEFAULT_FILE_STORAGE = 'django.core.files.storage.FileSystemStorage'

# Static & Media Files Configuration
STATIC_URL = 'static/'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATIC_ROOT = BASE_DIR / 'staticfiles'

# WhiteNoise configuration for static files
STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"
WHITENOISE_MAX_AGE = 31536000  # 1 year cache for static files
WHITENOISE_SKIP_COMPRESS_EXTENSIONS = ['.jpg', '.jpeg', '.png', '.gif', '.webp', '.svg', '.ico', '.mp4', '.webm']

# Media files configuration
MEDIA_URL = '/media/'
if USE_DIGITAL_OCEAN_SPACES and AWS_S3_CUSTOM_DOMAIN:
    # Use custom domain for Digital Ocean Spaces
    MEDIA_URL = f'https://{AWS_S3_CUSTOM_DOMAIN}/media/'
elif USE_DIGITAL_OCEAN_SPACES:
    # Use Spaces endpoint URL
    MEDIA_URL = f'{AWS_S3_ENDPOINT_URL}/{AWS_STORAGE_BUCKET_NAME}/media/'

MEDIA_ROOT = BASE_DIR / 'media'

# File upload settings
FILE_UPLOAD_MAX_MEMORY_SIZE = 10485760  # 10MB
DATA_UPLOAD_MAX_MEMORY_SIZE = 10485760  # 10MB

# ---------------------------------------
# Email Configuration
# ---------------------------------------
EMAIL_BACKEND_CONFIG = get_config('EMAIL_BACKEND', default='')
SENDGRID_API_KEY = get_config('SENDGRID_API_KEY', default='')
SENDGRID_SANDBOX_MODE = get_config('SENDGRID_SANDBOX_MODE_IN_DEBUG', default=True, cast_func=bool)

# Determine email backend
if EMAIL_BACKEND_CONFIG:
    EMAIL_BACKEND = EMAIL_BACKEND_CONFIG
elif DEBUG and SENDGRID_SANDBOX_MODE:
    EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
elif SENDGRID_API_KEY:
    EMAIL_BACKEND = 'sendgrid_backend.SendgridBackend'
else:
    # Fallback to SMTP
    EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'

# SMTP configuration
EMAIL_HOST = get_config('EMAIL_HOST', default='smtp.sendgrid.net')
EMAIL_PORT = get_config('EMAIL_PORT', default=587, cast_func=int)
EMAIL_USE_TLS = get_config('EMAIL_USE_TLS', default=True, cast_func=bool)
EMAIL_USE_SSL = get_config('EMAIL_USE_SSL', default=False, cast_func=bool)
EMAIL_HOST_USER = get_config('EMAIL_HOST_USER', default='apikey')
EMAIL_HOST_PASSWORD = SENDGRID_API_KEY if SENDGRID_API_KEY else get_config('EMAIL_HOST_PASSWORD', default='')
DEFAULT_FROM_EMAIL = get_config('DEFAULT_FROM_EMAIL', default='internmatchingcvsu@gmail.com')
SERVER_EMAIL = DEFAULT_FROM_EMAIL
EMAIL_SUBJECT_PREFIX = '[CVSU Internship] '
EMAIL_TIMEOUT = 30

# ---------------------------------------
# Channels & WebSockets Configuration
# ---------------------------------------
ASGI_APPLICATION = 'cvsu_internship.asgi.application'

CHANNEL_LAYERS = {
    'default': {
        'BACKEND': 'channels_redis.core.RedisChannelLayer',
        'CONFIG': {
            'hosts': [(get_config('REDIS_URL', default='rediss://localhost:6379'))],
            'capacity': 1500,  # default 100
            'expiry': 10,  # default 60
        },
    },
}

# ---------------------------------------
# Crispy Forms Configuration
# ---------------------------------------
CRISPY_ALLOWED_TEMPLATE_PACKS = "bootstrap5"
CRISPY_TEMPLATE_PACK = "bootstrap5"

# ---------------------------------------
# OnlyOffice Configuration
# ---------------------------------------
ONLYOFFICE_URL = get_config('ONLYOFFICE_URL', default='http://localhost/')
if ONLYOFFICE_URL.endswith('/'):
    ONLYOFFICE_URL = ONLYOFFICE_URL.rstrip('/')

ONLYOFFICE_SECRET = get_config('ONLYOFFICE_SECRET', default='your-local-secret')
ONLYOFFICE_VERIFY_PEER = get_config('ONLYOFFICE_VERIFY_PEER', default=False, cast_func=bool)

# ---------------------------------------
# Logging Configuration
# ---------------------------------------
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
            'style': '{',
        },
        'simple': {
            'format': '{levelname} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'simple',
            'stream': sys.stdout,
        },
        'file': {
            'class': 'logging.FileHandler',
            'filename': BASE_DIR / 'debug.log',
            'formatter': 'verbose',
        },
    },
    'loggers': {
        'django': {
            'handlers': ['console'],
            'level': get_config('DJANGO_LOG_LEVEL', default='INFO'),
            'propagate': True,
        },
        'cvsu_internship': {
            'handlers': ['console', 'file'],
            'level': 'DEBUG' if DEBUG else 'INFO',
            'propagate': False,
        },
    },
}

# ---------------------------------------
# Session & Cache Configuration
# ---------------------------------------
SESSION_ENGINE = 'django.contrib.sessions.backends.cached_db'
SESSION_COOKIE_AGE = 1209600  # 2 weeks in seconds
SESSION_COOKIE_NAME = 'cvsu_internship_session'

CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.redis.RedisCache',
        'LOCATION': get_config('REDIS_URL', default='rediss://localhost:6379/0'),
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
        }
    }
}

# ---------------------------------------
# Internationalization
# ---------------------------------------
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'Asia/Manila'
USE_I18N = True
USE_L10N = True
USE_TZ = True

# Locale paths
LOCALE_PATHS = [
    BASE_DIR / 'locale',
]

# ---------------------------------------
# Custom Settings
# ---------------------------------------
# Maximum file size for uploads (in bytes)
MAX_UPLOAD_SIZE = 10 * 1024 * 1024  # 10MB

# Allowed file extensions
ALLOWED_FILE_EXTENSIONS = {
    'image': ['.jpg', '.jpeg', '.png', '.gif', '.webp', '.svg'],
    'document': ['.pdf', '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx', '.txt'],
    'video': ['.mp4', '.webm', '.avi', '.mov'],
}

# ---------------------------------------
# Helper Functions
# ---------------------------------------
def get_absolute_media_url(relative_url):
    """Convert relative media URL to absolute URL for OnlyOffice"""
    if not relative_url:
        return ""
    
    # If already absolute (Cloudinary or Spaces)
    if relative_url.startswith(('http://', 'https://')):
        return relative_url
    
    # For production with Digital Ocean Spaces
    if USE_DIGITAL_OCEAN_SPACES:
        if AWS_S3_CUSTOM_DOMAIN:
            return f'https://{AWS_S3_CUSTOM_DOMAIN}/media/{relative_url}'
        else:
            return f'{AWS_S3_ENDPOINT_URL}/{AWS_STORAGE_BUCKET_NAME}/media/{relative_url}'
    
    # For production without Spaces
    if not DEBUG:
        return f"{BASE_URL}/media/{relative_url}"
    
    # For local development
    return f"http://localhost:8000/media/{relative_url}"

# ---------------------------------------
# Debug Output
# ---------------------------------------
if DEBUG:
    print("\n" + "="*60)
    print("CONFIGURATION VERIFICATION (DEBUG MODE)")
    print("="*60)
    print(f"Running on: {'RENDER' if 'RENDER' in os.environ else 'LOCAL'}")
    print(f"SECRET_KEY loaded: {'YES' if SECRET_KEY else 'NO'}")
    print(f"DEBUG mode: {DEBUG}")
    print(f"Database: {DATABASES['default']['ENGINE']}")
    print(f"SENDGRID_API_KEY loaded: {'YES' if SENDGRID_API_KEY else 'NO'}")
    print(f"Digital Ocean Spaces: {'ENABLED' if USE_DIGITAL_OCEAN_SPACES else 'DISABLED'}")
    print(f"Cloudinary: {'ENABLED' if USE_CLOUDINARY else 'DISABLED'}")
    print(f"Storage Backend: {DEFAULT_FILE_STORAGE}")
    print(f"Media URL: {MEDIA_URL}")
    print(f"ONLYOFFICE_URL: {ONLYOFFICE_URL}")
    print(f"Email Backend: {EMAIL_BACKEND}")
    print(f"Allowed Hosts: {ALLOWED_HOSTS}")
    print(f"CSRF Trusted Origins: {CSRF_TRUSTED_ORIGINS}")
    print("="*60)