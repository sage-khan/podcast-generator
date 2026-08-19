"""
Django settings for the Podcast Generator AI media platform
(image/character generation + LoRA fine-tuning, video, audio/TTS, podcasts).

For the full list of settings and their values, see
https://docs.djangoproject.com/en/4.2/ref/settings/
"""

import os
from pathlib import Path

# Environment detection
ENVIRONMENT = os.environ.get('DJANGO_ENVIRONMENT', 'development')
IS_PRODUCTION = ENVIRONMENT in ['production', 'staging']
IS_LOCAL = ENVIRONMENT == 'development'

# Load environment variables with priority system
if IS_LOCAL and not os.environ.get('CI'):
    # Local development - use .env file
    try:
        from dotenv import load_dotenv
        load_dotenv()  # take environment variables from .env
        print(f" [LOCAL] Loaded environment variables from .env file")
    except ImportError:
        print(" python-dotenv not installed, using environment variables directly")
        
elif IS_PRODUCTION or os.environ.get('CI'):
    # Production/CI - use environment variables directly (from GitHub Actions)
    print(f" [PRODUCTION] Using environment variables from system/GitHub Actions")
    
else:
    # Fallback
    print(f" [FALLBACK] Environment: {ENVIRONMENT}, using system environment variables")

# Verify critical environment variables are set
required_env_vars = [
    'POSTGRES_DB', 'POSTGRES_USER', 'POSTGRES_PASSWORD',
    'DO_SPACES_KEY', 'DO_SPACES_SECRET'
]

missing_vars = [var for var in required_env_vars if not os.environ.get(var)]
if missing_vars:
    print(f" Missing required environment variables: {missing_vars}")
    if IS_PRODUCTION:
        raise ValueError(f"Required environment variables not set: {missing_vars}")
else:
    print(f" All required environment variables are set")

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/4.2/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
# DJANGO_SECRET_KEY must be set via environment/.env in any real deployment.
# The fallback below is only for local development and is not secret.
SECRET_KEY = os.environ.get('DJANGO_SECRET_KEY') or 'django-insecure-local-dev-key-do-not-use-in-production'

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = os.environ.get('DJANGO_DEBUG', 'False').lower() in ['true', '1', 't']

# Robust ALLOWED_HOSTS build logic
# CRITICAL_HOSTS are always allowed in addition to DJANGO_ALLOWED_HOSTS (e.g. a
# stable droplet/load-balancer IP that must keep working even if the env var
# is misconfigured). Set as a comma-separated env var; empty by default.
CRITICAL_HOSTS = [h.strip() for h in os.environ.get('CRITICAL_HOSTS', '').split(',') if h.strip()]

raw_allowed_hosts = os.getenv('DJANGO_ALLOWED_HOSTS') or ''

# Split, strip, and discard empties
ALLOWED_HOSTS = [h.strip() for h in raw_allowed_hosts.split(',') if h and h.strip()]

# Ensure critical hosts are present
for host in CRITICAL_HOSTS:
    if host not in ALLOWED_HOSTS:
        ALLOWED_HOSTS.append(host)

# If the list is still empty (e.g. no env var and running locally)
if not ALLOWED_HOSTS:
    ALLOWED_HOSTS = ['localhost', '127.0.0.1', *CRITICAL_HOSTS]

# Application definition

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    
    # Third-party apps
    'rest_framework',
    'rest_framework.authtoken',  # Add this for token authentication
    'corsheaders',
    'drf_yasg',  # Swagger/OpenAPI documentation
    
    # Project apps
    'image_generation.apps.ImageGenerationConfig',
    'video_generation.apps.VideoGenerationConfig',
    'audio_generation.apps.AudioGenerationConfig',
    'model_training.apps.ModelTrainingConfig',
    'podcast_generator.apps.PodcastGeneratorConfig',
    'shared',  # Shared utilities and components
    'playground',  # Playground UI for testing various generation models
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'corsheaders.middleware.CorsMiddleware',  # CORS middleware
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

# CORS settings
CORS_ALLOW_ALL_ORIGINS = True
CORS_ALLOW_CREDENTIALS = True

# REST Framework settings
REST_FRAMEWORK = {
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.AllowAny',
    ],

    # <<<  ADD THIS BLOCK  >>>
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework.authentication.TokenAuthentication',
        'rest_framework.authentication.SessionAuthentication',  # optional
    ],
    # <<<  END ADD  >>>

    'DEFAULT_RENDERER_CLASSES': [
        'rest_framework.renderers.JSONRenderer',
        'rest_framework.renderers.BrowsableAPIRenderer',
    ],
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 20,
}

ROOT_URLCONF = 'config.urls'

# Send @login_required views to the Django admin's login page since this
# project doesn't ship a separate accounts/auth UI.
LOGIN_URL = '/admin/login/'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [os.path.join(BASE_DIR, 'templates')],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'

# Database
# https://docs.djangoproject.com/en/4.2/ref/settings/#databases

def get_database_config():
    """
    Get database configuration with SSL fallback support.
    Uses SSL with verify-ca only in Kubernetes environments.
    Disables SSL for DigitalOcean Droplets running PostgreSQL in Docker.
    """
    import os
    import socket
    import pathlib
    
    # Improved environment detection 
    hostname = socket.gethostname()
    
    # More comprehensive DigitalOcean Droplet detection
    # Check hostname patterns, common paths, and environment indicators
    droplet_indicators = [
        'ubuntu' in hostname.lower(),
        hostname.startswith('s-'),
        'droplet' in hostname.lower(),
        os.path.exists('/var/www/podcast-generator'),
        os.path.exists('/root/.digitalocean_password'),
        os.path.exists('/etc/apt/sources.list.d/digitalocean-agent.list'),
        # Current path check - if we're in /var/www, we're likely on the droplet
        str(pathlib.Path.cwd()).startswith('/var/www')
    ]
    on_droplet = any(droplet_indicators)
    
    # More reliable K8s detection
    k8s_env = (os.path.exists('/var/run/secrets/kubernetes.io') or 
              'KUBERNETES_SERVICE_HOST' in os.environ)
    
    force_ssl = os.environ.get('POSTGRES_FORCE_SSL', '').lower() in ['true', '1', 't']
    
    print(f"Environment detection: K8s={k8s_env}, On Droplet={on_droplet}, Force SSL={force_ssl}")
    print(f"Current path: {os.getcwd()}")
    print(f"Hostname: {hostname}")
    
    # Choose correct variable set: use MANAGED_PG_* when present (Kubernetes)
    db_name = os.environ.get('MANAGED_PG_DB') or os.environ.get('POSTGRES_DB')
    db_user = os.environ.get('MANAGED_PG_USER') or os.environ.get('POSTGRES_USER')
    db_password = os.environ.get('MANAGED_PG_PASSWORD') or os.environ.get('POSTGRES_PASSWORD')
    db_host = os.environ.get('MANAGED_PG_HOST') or os.environ.get('DB_HOST', 'db')
    db_port = os.environ.get('MANAGED_PG_PORT') or os.environ.get('DB_PORT', '5432')
    
    # Determine SSL mode: verify-ca on kubernetes / managed DB, disable otherwise
    if os.environ.get('MANAGED_PG_HOST') or (k8s_env and not on_droplet):
        ssl_mode = 'verify-ca'
    else:
        ssl_mode = 'disable'
        
    return {
        'ENGINE': os.environ.get('DB_ENGINE', 'django.db.backends.postgresql'),
        'NAME': db_name,
        'USER': db_user,
        'PASSWORD': db_password,
        'HOST': db_host,
        'PORT': db_port,
        'OPTIONS': {
            'sslmode': ssl_mode,
            # Expect CA cert to be mounted by init-container when ssl enabled
            **({ 'sslrootcert': '/etc/ssl/certs/postgres-ca.crt' } if ssl_mode == 'verify-ca' else {})
        }
    }

# Use the function to get the appropriate database configuration
DATABASES = {
    'default': get_database_config()
}

# Password validation
# https://docs.djangoproject.com/en/4.2/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

# Internationalization
# https://docs.djangoproject.com/en/4.2/topics/i18n/

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

# Static files configuration
# STATIC_URL is the URL path where static files will be served from
# STATIC_ROOT is the absolute path where collectstatic will gather files
# Using /app/static for both Docker and K8s environments for consistency
STATIC_URL = '/static/'
STATIC_ROOT = '/app/static'

# STATICFILES_DIRS can specify additional locations for static files
# Empty to avoid conflicts, as all static files should be in app directories
# or collected directly to STATIC_ROOT
STATICFILES_DIRS = []

# Ensure admin and API docs static files are properly collected
# This is Django's default behavior, but we're being explicit
STATICFILES_FINDERS = [
    'django.contrib.staticfiles.finders.FileSystemFinder',
    'django.contrib.staticfiles.finders.AppDirectoriesFinder',
]

# Media files (user uploads)
MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')

# Celery Configuration
CELERY_BROKER_URL = 'redis://redis:6379/0'
CELERY_RESULT_BACKEND = 'redis://redis:6379/0'
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = TIME_ZONE
CELERY_BROKER_CONNECTION_RETRY = True
CELERY_BROKER_CONNECTION_RETRY_ON_STARTUP = True
CELERY_BROKER_CONNECTION_MAX_RETRIES = 10

# Replicate API Configuration
REPLICATE_API_TOKEN = os.getenv("REPLICATE_API_TOKEN")
REPLICATE_LORA_TRAINER_MODEL = os.environ.get('REPLICATE_LORA_TRAINER_MODEL', 'flux-labs/lora-training:53a24189e4ecb755fa2b8d39224d42fca2e33f44095944a2e6e8d695a19addc1')
REPLICATE_CHARACTER_MODEL = os.environ.get('REPLICATE_CHARACTER_MODEL', 'stability-ai/sdxl:c221b2b8ef527988fb59bf24a8b97c4561f1c671f73bd389f866bfb27c061316')
REPLICATE_POSE_MODEL = os.environ.get('REPLICATE_POSE_MODEL', 'stability-ai/sdxl:c221b2b8ef527988fb59bf24a8b97c4561f1c671f73bd389f866bfb27c061316')
DEFAULT_REPLICATE_OWNER = os.environ.get('REPLICATE_OWNER', 'your-replicate-username')

# OpenRouter API Configuration
OPENROUTER_API_KEY = os.environ.get('OPENROUTER_API_KEY')

# Storage Configuration
STORAGE_BACKEND = os.environ.get('STORAGE_BACKEND', 'local')  # Options: 'local', 'do_spaces'
LOCAL_STORAGE_BASE_PATH = os.environ.get('LOCAL_STORAGE_BASE_PATH', os.path.join(BASE_DIR, 'media'))
DO_SPACES_BUCKET = os.environ.get('DO_SPACES_BUCKET')
DO_SPACES_REGION = os.environ.get('DO_SPACES_REGION', 'nyc3')
DO_SPACES_KEY = os.environ.get('DO_SPACES_KEY')
DO_SPACES_SECRET = os.environ.get('DO_SPACES_SECRET')

 

# Webhook Base URL
# Detect if running in Kubernetes by checking for K8S environment variable or file
K8S_ENV = os.path.exists('/var/run/secrets/kubernetes.io') or 'KUBERNETES_SERVICE_HOST' in os.environ
if K8S_ENV:
    # If running in Kubernetes, use the K8S webhook base URL
    WEBHOOK_BASE_URL = os.environ.get('K8S_WEBHOOK_BASE_URL', f"https://{os.environ.get('K8S_DOMAIN', ALLOWED_HOSTS[0] if ALLOWED_HOSTS else 'localhost')}")
else:
    # Otherwise use standard webhook base URL (for Droplet)
    WEBHOOK_BASE_URL = os.environ.get('WEBHOOK_BASE_URL', f"https://{ALLOWED_HOSTS[0]}")

# Security settings for running behind a reverse proxy (like Nginx)
# Ensure Nginx sets X-Forwarded-Proto and X-Forwarded-Host headers
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
USE_X_FORWARDED_HOST = True
SECURE_SSL_REDIRECT = False  # Nginx should handle the redirect if needed

# Logging Configuration
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
            'level': 'INFO',
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'INFO',
    },
    'loggers': {
        'django': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False,
        },
        'image_generation': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False,
        },
        'video_generation': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False,
        },
        'audio_generation': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False,
        },
        'podcast_generator': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False,
        },
        'model_training': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False,
        },
        'shared': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False,
        },
    },
}
