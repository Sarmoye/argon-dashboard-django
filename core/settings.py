# -*- encoding: utf-8 -*-
"""
Copyright (c) 2019 - present AppSeed.us
"""

from decouple import config
from unipath import Path
import random, string, os

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
BASE_DIR = Path(__file__).parent
CORE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.environ.get('SECRET_KEY')
if not SECRET_KEY:
    SECRET_KEY = ''.join(random.choice( string.ascii_lowercase  ) for i in range( 32 ))

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

# load production server from .env
ALLOWED_HOSTS = ['ems.mtn.bj','localhost', '127.0.0.1', '10.77.8.91', config('SERVER', default='127.0.0.1')]
AUTH_USER_MODEL = 'authentication.CustomUser'
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Application definition

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'apps.home',  # Enable the inner home (home)
    'apps.authentication',
    'apps.sources_data_app',
    'apps.analysis',
    'apps.error_management_systems',
    'rest_framework',
    'rest_framework_simplejwt',
    'rest_framework.authtoken', #keep this for the admin interface.
    'django_celery_beat'
]

# Cookies
SESSION_COOKIE_SECURE = False      # ⚠️ Important vu que tu es en HTTP
CSRF_COOKIE_SECURE = False         # idem, sinon CSRF échouera

# Samesite: peut être 'Lax', 'Strict' ou 'None' (mais 'None' nécessite HTTPS + Secure)
SESSION_COOKIE_SAMESITE = 'Lax'    # recommandé pour les apps classiques

# Tu peux garder ça si tu es derrière Nginx
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')


REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ],
}

from datetime import timedelta

SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=15),  # Adjust as needed (15 mins example)
    'REFRESH_TOKEN_LIFETIME': timedelta(days=1),     # Adjust as needed (1 day example)
    'ROTATE_REFRESH_TOKENS': False,
    'BLACKLIST_AFTER_ROTATION': True,
    'ALGORITHM': 'HS256',
    'SIGNING_KEY': SECRET_KEY,  # Use your Django SECRET_KEY
    'VERIFYING_KEY': None,
    'AUTH_HEADER_TYPES': ('Bearer',),
    'USER_ID_FIELD': 'id',
    'USER_ID_CLAIM': 'user_id',
    'AUTH_TOKEN_CLASSES': ('rest_framework_simplejwt.tokens.AccessToken',),
    'TOKEN_TYPE_CLAIM': 'token_type',
}

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

ROOT_URLCONF = 'core.urls'
LOGIN_URL = '/authentication/login/'
TEMPLATE_DIR = os.path.join(CORE_DIR, "apps/templates")  # ROOT dir for templates

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [TEMPLATE_DIR],
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

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'file': {
            'level': 'ERROR',
            'class': 'logging.FileHandler',
            'filename': 'ems_logs.log',
        },
    },
    'loggers': {
        'django': {
            'handlers': ['file'],
            'level': 'ERROR',
            'propagate': True,
        },
    },
}


WSGI_APPLICATION = 'core.wsgi.application'

# Database
# https://docs.djangoproject.com/en/3.0/ref/settings/#databases

""" DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': 'db.sqlite3',
    }
} """

DB_ENGINE='postgresql'
DB_NAME='itsea_db'
DB_USERNAME='ems_user'
DB_PASS="ems@!1&112024"
DB_HOST='10.77.8.93'
DB_PORT=5432
DB_ATOMIC=True
DB_CONN_HEALTH_CHECKS=True

DATABASES = { 
    'default': {
        'ENGINE': f'django.db.backends.{DB_ENGINE}',
        'NAME': DB_NAME,
        'USER': DB_USERNAME,
        'PASSWORD': DB_PASS,
        'HOST': DB_HOST,
        'PORT': DB_PORT,
        'ATOMIC_REQUESTS': DB_ATOMIC == 'True',
        'CONN_MAX_AGE': 600,  # Optional: maintain persistent connections
        'CONN_HEALTH_CHECKS': DB_CONN_HEALTH_CHECKS,
    }
}

# Password validation
# https://docs.djangoproject.com/en/3.0/ref/settings/#auth-password-validators

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
# https://docs.djangoproject.com/en/3.0/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_L10N = True

USE_TZ = True

#############################################################
# SRC: https://devcenter.heroku.com/articles/django-assets

# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/1.9/howto/static-files/
STATIC_ROOT = os.path.join(CORE_DIR, 'staticfiles')
STATIC_URL = '/static/'

# Extra places for collectstatic to find static files.
STATICFILES_DIRS = (
    os.path.join(CORE_DIR, 'apps/static'),
)


# Configurations Celery
CELERY_BROKER_URL = 'redis://localhost:6379/0'  # Utiliser Redis sur localhost, port 6379, base de données 0
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_BACKEND = 'redis://localhost:6379/0'  # Utilise Redis pour stocker les résultats des tâches

# Dans celeryconfig.py ou settings.py
from celery.schedules import crontab

PRESTO_SERVER="https://lnx-eva-master01.mtn.bj"
PRESTO_PORT="8443"
PRESTO_CATALOG="hive"
PRESTO_SCHEMA="hive"
PRESTO_USER="itsea_user_svc"
PRESTO_PASSWORD="g3$JdBv2C3t#Tc&JjK57@8/qA)"
PRESTO_KEYSTORE_PATH="/etc/nginx/sites-available/argon-dashboard-django/eva_key/benin_keystore.jks"
PRESTO_KEYSTORE_PASSWORD="enzoslR722$"

# Configuration de connexion à Presto
presto_config = {
    "PRESTO_SERVER": PRESTO_SERVER,
    "PRESTO_PORT": PRESTO_PORT,
    "PRESTO_CATALOG": PRESTO_CATALOG, 
    "PRESTO_SCHEMA": PRESTO_SCHEMA,
    "PRESTO_USER": PRESTO_USER,
    "PRESTO_PASSWORD": PRESTO_PASSWORD,
    "PRESTO_KEYSTORE_PATH": PRESTO_KEYSTORE_PATH,
    "PRESTO_KEYSTORE_PASSWORD": PRESTO_KEYSTORE_PASSWORD
}

# Celery Beat Configuration
CELERY_BEAT_SCHEDULE = {
    'cis-error-report-every-20min': {
        'task': 'apps.error_management_systems.tasks.task_execute_cis_error_report',
        'schedule': timedelta(minutes=5),  # Exécution toutes les 5 minutes
        'args': (presto_config, '/srv/itsea_files/error_report_files')
    },
}

#############################################################
#############################################################
