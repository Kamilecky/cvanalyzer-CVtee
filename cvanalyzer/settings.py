"""
cvanalyzer/settings.py - Konfiguracja projektu AI CV Analyzer.

Obsługuje SQLite (dev) i PostgreSQL (prod) poprzez zmienne środowiskowe.
Zawiera konfigurację: OpenAI, Celery+Redis, Stripe, email SMTP, plany subskrypcyjne.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / '.env')

# ---------------------------------------------------------------------------
# Bezpieczeństwo
# ---------------------------------------------------------------------------
SECRET_KEY = os.environ.get(
    'DJANGO_SECRET_KEY',
    'django-insecure-cvanalyzer-dev-key-change-in-production'
)
DEBUG = os.environ.get('DJANGO_DEBUG', 'True') == 'True'
ALLOWED_HOSTS = os.environ.get('ALLOWED_HOSTS', 'localhost,127.0.0.1').split(',')

# ---------------------------------------------------------------------------
# Aplikacje
# ---------------------------------------------------------------------------
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    # Third-party
    'rest_framework',
    # Local apps
    'accounts',
    'cv',
    'analysis',
    'jobs',
    'billing',
    'reports',
    'recruitment',
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

ROOT_URLCONF = 'cvanalyzer.urls'

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
            ],
        },
    },
]

WSGI_APPLICATION = 'cvanalyzer.wsgi.application'

# ---------------------------------------------------------------------------
# Baza danych - SQLite (dev) / PostgreSQL (prod)
# ---------------------------------------------------------------------------
DATABASES = {
    'default': {
        'ENGINE': os.environ.get('DB_ENGINE', 'django.db.backends.sqlite3'),
        'NAME': os.environ.get('DB_NAME', str(BASE_DIR / 'db.sqlite3')),
        'USER': os.environ.get('DB_USER', ''),
        'PASSWORD': os.environ.get('DB_PASSWORD', ''),
        'HOST': os.environ.get('DB_HOST', ''),
        'PORT': os.environ.get('DB_PORT', ''),
    }
}

# ---------------------------------------------------------------------------
# Walidacja haseł
# ---------------------------------------------------------------------------
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# ---------------------------------------------------------------------------
# Autoryzacja - niestandardowy model użytkownika
# ---------------------------------------------------------------------------
AUTH_USER_MODEL = 'accounts.User'
LOGIN_URL = '/accounts/login/'
LOGIN_REDIRECT_URL = '/analysis/'
LOGOUT_REDIRECT_URL = '/accounts/login/'

# ---------------------------------------------------------------------------
# Lokalizacja
# ---------------------------------------------------------------------------
LANGUAGE_CODE = 'en'
TIME_ZONE = 'Europe/Warsaw'
USE_I18N = True
USE_TZ = True

# ---------------------------------------------------------------------------
# Pliki statyczne i media
# ---------------------------------------------------------------------------
STATIC_URL = '/static/'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATIC_ROOT = BASE_DIR / 'staticfiles'

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# ---------------------------------------------------------------------------
# Limity uploadu plików (10 MB)
# ---------------------------------------------------------------------------
FILE_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024
DATA_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# ---------------------------------------------------------------------------
# Email (Gmail SMTP)
# ---------------------------------------------------------------------------
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = 'smtp.gmail.com'
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_USE_SSL = False
EMAIL_HOST_USER = os.environ.get('EMAIL_HOST_USER', 'kpl50970@gmail.com')
EMAIL_HOST_PASSWORD = os.environ.get('EMAIL_HOST_PASSWORD', 'iqfc nzmr hnrj xwai')
DEFAULT_FROM_EMAIL = os.environ.get('DEFAULT_FROM_EMAIL', 'kpl50970@gmail.com')

# Weryfikacja email
REQUIRE_EMAIL_VERIFICATION = True
EMAIL_VERIFICATION_TOKEN_EXPIRY_HOURS = 24

# ---------------------------------------------------------------------------
# Plany subskrypcyjne - limity miesięcznych analiz
# ---------------------------------------------------------------------------
PLAN_LIMITS = {
    'free': 15,
    'pro': None,      # unlimited
    'premium': None,   # unlimited
}

# Macierz funkcji dostępnych w poszczególnych planach
PLAN_FEATURES = {
    'free': {
        'basic_scoring': True,
        'section_detection': True,
        'problem_detection': True,
        'recommendations': False,
        'job_matching': True,
        'pdf_export': False,
        'ai_rewriting': False,
        'skill_gap': False,
        'benchmarking': False,
        'career_advisor': False,
        'cv_versioning': False,
        'recruitment': True,
        'candidate_ranking': True,
        'red_flags': True,
        'interview_questions': False,
        'market_benchmark': False,
    },
    'pro': {
        'basic_scoring': True,
        'section_detection': True,
        'problem_detection': True,
        'recommendations': True,
        'job_matching': True,
        'pdf_export': True,
        'skill_gap': True,
        'ai_rewriting': False,
        'benchmarking': False,
        'career_advisor': False,
        'cv_versioning': True,
        'recruitment': True,
        'candidate_ranking': True,
        'red_flags': True,
        'interview_questions': False,
        'market_benchmark': False,
    },
    'premium': {
        'basic_scoring': True,
        'section_detection': True,
        'problem_detection': True,
        'recommendations': True,
        'job_matching': True,
        'pdf_export': True,
        'skill_gap': True,
        'ai_rewriting': True,
        'benchmarking': True,
        'career_advisor': True,
        'cv_versioning': True,
        'recruitment': True,
        'candidate_ranking': True,
        'red_flags': True,
        'interview_questions': True,
        'market_benchmark': True,
    },
}

# ---------------------------------------------------------------------------
# OpenAI
# ---------------------------------------------------------------------------
OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY', '')
OPENAI_MODEL = os.environ.get('OPENAI_MODEL', 'gpt-4o-mini')
OPENAI_MAX_TOKENS = 2048
OPENAI_TEMPERATURE = 0

# ---------------------------------------------------------------------------
# Celery + Redis
# ---------------------------------------------------------------------------
CELERY_BROKER_URL = os.environ.get('CELERY_BROKER_URL', 'redis://localhost:6379/0')
CELERY_RESULT_BACKEND = os.environ.get('CELERY_RESULT_BACKEND', 'redis://localhost:6379/0')
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = 'Europe/Warsaw'

# Celery Beat - zaplanowane zadania cykliczne (opcjonalne, wymaga Redis)
try:
    from celery.schedules import crontab
    CELERY_BEAT_SCHEDULE = {
        'reset-monthly-usage': {
            'task': 'billing.tasks.reset_monthly_usage',
            'schedule': crontab(day_of_month='1', hour='0', minute='0'),
        },
    }
except ImportError:
    CELERY_BEAT_SCHEDULE = {}

# ---------------------------------------------------------------------------
# Stripe
# ---------------------------------------------------------------------------
STRIPE_PUBLIC_KEY = os.environ.get('STRIPE_PUBLIC_KEY', '')
STRIPE_SECRET_KEY = os.environ.get('STRIPE_SECRET_KEY', '')
STRIPE_WEBHOOK_SECRET = os.environ.get('STRIPE_WEBHOOK_SECRET', '')

# ---------------------------------------------------------------------------
# Django REST Framework (przygotowane na przyszłe API)
# ---------------------------------------------------------------------------
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework.authentication.SessionAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
}
