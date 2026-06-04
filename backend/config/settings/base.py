import os
from pathlib import Path
import environ

env = environ.Env()

BASE_DIR = Path(__file__).resolve().parent.parent.parent

env.read_env(BASE_DIR.parent / ".env")

SECRET_KEY = env.str("DJANGO_SECRET_KEY", default="insecure-dev-key-change-in-production")
DEBUG = env.bool("DJANGO_DEBUG", default=True)
ALLOWED_HOSTS = env.list("DJANGO_ALLOWED_HOSTS", default=["localhost", "127.0.0.1"])

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # Third-party
    "rest_framework",
    "rest_framework.authtoken",
    "corsheaders",
    "django_filters",
    # Local apps
    "apps.agents",
    "apps.workflows",
    "apps.executions",
    "apps.history",
    "apps.telegram",
]

MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

DATABASES = {
    "default": env.db("DATABASE_URL", default="postgres://yunoai:yunoai@localhost:5432/yunoai"),
}

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
]

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Redis / Celery
REDIS_URL = env.str("REDIS_URL", default="redis://localhost:6379/0")
CELERY_BROKER_URL = env.str("CELERY_BROKER_URL", default="redis://localhost:6379/1")
CELERY_RESULT_BACKEND = CELERY_BROKER_URL
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_TIMEZONE = "UTC"

# CORS
CORS_ALLOW_ALL_ORIGINS = DEBUG
CORS_ALLOWED_ORIGINS = env.list("CORS_ALLOWED_ORIGINS", default=["http://localhost:3000"])

# REST Framework
REST_FRAMEWORK = {
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 50,
    "DEFAULT_FILTER_BACKENDS": [
        "django_filters.rest_framework.DjangoFilterBackend",
        "rest_framework.filters.SearchFilter",
        "rest_framework.filters.OrderingFilter",
    ],
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework.authentication.SessionAuthentication",
        "rest_framework.authentication.BasicAuthentication",
        "rest_framework.authentication.TokenAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
}

# LLM Provider Settings
LLM_PROVIDERS = {
    "deepseek": {
        "api_key": env.str("DEEPSEEK_API_KEY", default=""),
        "api_base": env.str("DEEPSEEK_API_BASE", default="https://api.deepseek.com/v1"),
        "default_model": env.str("DEEPSEEK_DEFAULT_MODEL", default="deepseek-chat"),
    },
    "opencode": {
        "api_key": env.str("OPENCODE_API_KEY", default=""),
        "api_base": env.str("OPENCODE_API_BASE", default="https://api.opencode.ai/v1"),
        "default_model": env.str("OPENCODE_DEFAULT_MODEL", default="opencode-default"),
    },
    "grok": {
        "api_key": env.str("GROK_API_KEY", default=""),
        "api_base": env.str("GROK_API_BASE", default="https://api.x.ai/v1"),
        "default_model": env.str("GROK_DEFAULT_MODEL", default="grok-2-1212"),
    },
    "gemini": {
        "api_key": env.str("GEMINI_API_KEY", default=""),
        "api_base": env.str("GEMINI_API_BASE", default="https://generativelanguage.googleapis.com/v1beta"),
        "default_model": env.str("GEMINI_DEFAULT_MODEL", default="gemini-2.0-flash"),
    },
    "openai": {
        "api_key": env.str("OPENAI_API_KEY", default=""),
        "api_base": env.str("OPENAI_API_BASE", default="https://api.openai.com/v1"),
        "default_model": env.str("OPENAI_DEFAULT_MODEL", default="gpt-4o"),
    },
    "anthropic": {
        "api_key": env.str("ANTHROPIC_API_KEY", default=""),
        "api_base": env.str("ANTHROPIC_API_BASE", default="https://api.anthropic.com/v1"),
        "default_model": env.str("ANTHROPIC_DEFAULT_MODEL", default="claude-3-5-sonnet-20241022"),
    },
}

# Provider rate limits for quota-aware routing
#   rpm  = max requests per 60-second sliding window
#   daily = max requests per calendar day
PROVIDER_LIMITS = {
    "grok": {"rpm": 30, "daily": 7000},
    "gemini": {"rpm": 10, "daily": 1500},
    "deepseek": {"rpm": 60, "daily": 100000},
    "openai": {"rpm": 60, "daily": 500000},
    "anthropic": {"rpm": 60, "daily": 500000},
    "opencode": {"rpm": 60, "daily": 100000},
}

# Provider fallback chain — when primary provider fails, try these in order
PROVIDER_FALLBACK_CHAIN = {
    "grok": ["deepseek"],
    "gemini": ["grok", "deepseek"],
    "deepseek": ["grok", "opencode"],
    "openai": ["anthropic", "deepseek"],
    "anthropic": ["openai", "deepseek"],
    "opencode": ["deepseek", "grok"],
}

# Celery Beat Schedule
CELERY_BEAT_SCHEDULE = {
    "check-agent-schedules": {
        "task": "apps.agents.tasks.check_agent_schedules",
        "schedule": 60.0,  # every 60 seconds
    },
}

# Telegram
TELEGRAM_BOT_TOKEN = env.str("TELEGRAM_BOT_TOKEN", default="")
