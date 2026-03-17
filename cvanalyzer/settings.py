"""
cvanalyzer/settings.py - Konfiguracja projektu AI CV Analyzer.

Obsługuje SQLite (dev) i PostgreSQL (prod) poprzez zmienne środowiskowe.
Zawiera konfigurację: OpenAI, Celery+Redis, Stripe, email SMTP, plany subskrypcyjne.
"""

import os
from pathlib import Path
from dotenv import load_dotenv
import dj_database_url

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / '.env')

# ---------------------------------------------------------------------------
# Bezpieczeństwo
# ---------------------------------------------------------------------------
SECRET_KEY = os.environ.get(
    'DJANGO_SECRET_KEY',
    'django-insecure-cvanalyzer-dev-key-change-in-production'
)
DEBUG = os.environ.get('DJANGO_DEBUG', 'False') == 'True'
ALLOWED_HOSTS = ['*']
CSRF_TRUSTED_ORIGINS = [
    "https://cveeto.eu",
    "https://www.cveeto.eu",
]

# --- HTTPS / proxy ---
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_SSL_REDIRECT = True

# --- HSTS ---
SECURE_HSTS_SECONDS = 3600
SECURE_HSTS_INCLUDE_SUBDOMAINS = False
SECURE_HSTS_PRELOAD = False

# --- Cookies ---
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SESSION_COOKIE_HTTPONLY = True
CSRF_COOKIE_SAMESITE = "Lax"
SESSION_COOKIE_SAMESITE = "Lax"

# --- Rate limiting (django-ratelimit) — uses default Redis cache ---
RATELIMIT_USE_CACHE = 'default'
RATELIMIT_FAIL_OPEN = False   # blokuj przy braku cache, nie przepuszczaj

# --- Security headers ---
X_FRAME_OPTIONS = "DENY"
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_BROWSER_XSS_FILTER = True

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
    'django_ratelimit',
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
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.locale.LocaleMiddleware',
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
                'django.template.context_processors.i18n',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'accounts.context_processors.user_stats',
            ],
        },
    },
]

WSGI_APPLICATION = 'cvanalyzer.wsgi.application'

# ---------------------------------------------------------------------------
# Baza danych - PostgreSQL via DATABASE_URL
# ---------------------------------------------------------------------------
DATABASES = {
    'default': dj_database_url.config(
        default=os.environ.get("DATABASE_URL"),
        conn_max_age=600,
        ssl_require=True,
    )
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

LANGUAGES = [
    ('en', 'English'),
    ('pl', 'Polski'),
]

LOCALE_PATHS = [
    BASE_DIR / 'locale',
]

# ---------------------------------------------------------------------------
# Pliki statyczne i media
# ---------------------------------------------------------------------------
STATIC_URL = "/static/"
STATICFILES_DIRS = [BASE_DIR / 'static']
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_STORAGE = "whitenoise.storage.CompressedStaticFilesStorage"

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# ---------------------------------------------------------------------------
# Limity uploadu plików (10 MB)
# ---------------------------------------------------------------------------
FILE_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024
DATA_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# ---------------------------------------------------------------------------
# Email — Mailgun SMTP
# Wymagane zmienne środowiskowe na Railway:
#   MAILGUN_SMTP_LOGIN    — np. postmaster@mg.cveeto.eu
#   MAILGUN_SMTP_PASSWORD — klucz SMTP z panelu Mailgun
#   DEFAULT_FROM_EMAIL    — np. CVeeto <noreply@mg.cveeto.eu>
# Konto EU: użyj EMAIL_HOST = 'smtp.eu.mailgun.org'
# ---------------------------------------------------------------------------
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = os.environ.get('MAILGUN_SMTP_HOST', 'smtp.mailgun.org')
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_USE_SSL = False
EMAIL_HOST_USER = os.environ.get('MAILGUN_SMTP_LOGIN', '')
EMAIL_HOST_PASSWORD = os.environ.get('MAILGUN_SMTP_PASSWORD', '')
DEFAULT_FROM_EMAIL = os.environ.get('DEFAULT_FROM_EMAIL', 'CVeeto <noreply@cveeto.eu>')
SERVER_EMAIL = DEFAULT_FROM_EMAIL

# Weryfikacja email
REQUIRE_EMAIL_VERIFICATION = True
EMAIL_VERIFICATION_TOKEN_EXPIRY_HOURS = 24

# ---------------------------------------------------------------------------
# Plany subskrypcyjne - limity miesięcznych analiz
# ---------------------------------------------------------------------------
PLAN_LIMITS = {
    'free': 5,
    'basic': 50,
    'premium': 300,
    'enterprise': None,   # unlimited
}

# Limity aktywnych stanowisk pracy
JOB_POSITION_LIMITS = {
    'free': 3,
    'basic': 10,
    'premium': 50,
    'enterprise': None,   # unlimited
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
        'requirement_scoring': False,
        'priority_processing': False,
        'sla_flag': False,
        'custom_prompts': False,
        'api_access': False,
    },
    'basic': {
        'basic_scoring': True,
        'section_detection': True,
        'problem_detection': True,
        'recommendations': True,
        'job_matching': True,
        'pdf_export': False,
        'ai_rewriting': False,
        'skill_gap': True,
        'benchmarking': False,
        'career_advisor': False,
        'cv_versioning': True,
        'recruitment': True,
        'candidate_ranking': True,
        'red_flags': True,
        'interview_questions': False,
        'market_benchmark': False,
        'requirement_scoring': False,
        'priority_processing': False,
        'sla_flag': False,
        'custom_prompts': False,
        'api_access': False,
    },
    'premium': {
        'basic_scoring': True,
        'section_detection': True,
        'problem_detection': True,
        'recommendations': True,
        'job_matching': True,
        'pdf_export': True,
        'ai_rewriting': True,
        'skill_gap': True,
        'benchmarking': True,
        'career_advisor': True,
        'cv_versioning': True,
        'recruitment': True,
        'candidate_ranking': True,
        'red_flags': True,
        'interview_questions': True,
        'market_benchmark': True,
        'requirement_scoring': True,
        'priority_processing': False,
        'sla_flag': False,
        'custom_prompts': False,
        'api_access': False,
    },
    'enterprise': {
        'basic_scoring': True,
        'section_detection': True,
        'problem_detection': True,
        'recommendations': True,
        'job_matching': True,
        'pdf_export': True,
        'ai_rewriting': True,
        'skill_gap': True,
        'benchmarking': True,
        'career_advisor': True,
        'cv_versioning': True,
        'recruitment': True,
        'candidate_ranking': True,
        'red_flags': True,
        'interview_questions': True,
        'market_benchmark': True,
        'requirement_scoring': True,
        'priority_processing': True,
        'sla_flag': True,
        'custom_prompts': True,
        'api_access': True,
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
REDIS_URL = os.environ.get('REDIS_URL', 'redis://localhost:6379/0')

# Django cache — uses Redis (built-in backend since Django 4.0, no extra package needed)
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.redis.RedisCache',
        'LOCATION': REDIS_URL,
        'KEY_PREFIX': 'cveeto',
        'TIMEOUT': 300,
    }
}

CELERY_BROKER_URL = os.environ.get('CELERY_BROKER_URL', REDIS_URL)
CELERY_RESULT_BACKEND = os.environ.get('CELERY_RESULT_BACKEND', REDIS_URL)
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
