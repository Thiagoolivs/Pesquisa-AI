import os
from pathlib import Path
from dotenv import load_dotenv
import dj_database_url

# =========================
# BASE
# =========================
BASE_DIR = Path(__file__).resolve().parent.parent.parent

# =========================
# ENV
# =========================
load_dotenv()

# =========================
# SECURITY
# =========================
SECRET_KEY = os.getenv(
    "SECRET_KEY",
    "django-insecure-change-this-in-production"
)

DEBUG = os.getenv("DEBUG", "True") == "True"

ALLOWED_HOSTS = ["*"]

# =========================
# APPS
# =========================
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "pesquisa_ai.core",
]

# =========================
# MIDDLEWARE
# =========================
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
]

# =========================
# URLS / WSGI
# =========================
ROOT_URLCONF = "pesquisa_ai.config.urls"
WSGI_APPLICATION = "pesquisa_ai.config.wsgi.application"

# =========================
# TEMPLATES
# =========================
TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
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

# =========================
# DATABASE
# =========================
if DEBUG:
    # SQLite (desenvolvimento)
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / os.getenv("SQLITE_DB", "db.sqlite3"),
        }
    }
else:
    # PostgreSQL (produção)
    DATABASES = {
        "default": dj_database_url.parse(
            os.getenv("DATABASE_URL"),
            conn_max_age=600,
            ssl_require=False,
        )
    }

# =========================
# INTERNACIONALIZAÇÃO
# =========================
LANGUAGE_CODE = "pt-br"
TIME_ZONE = "America/Sao_Paulo"
USE_I18N = True
USE_TZ = True

# =========================
# STATIC FILES
# =========================
STATIC_URL = "/static/"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = BASE_DIR / "staticfiles"

# =========================
# DEFAULT FIELD
# =========================
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# =========================
# UPLOAD LIMITS
# =========================
DATA_UPLOAD_MAX_MEMORY_SIZE = 50 * 1024 * 1024   # 50 MB (default 2.5 MB is too small)
FILE_UPLOAD_MAX_MEMORY_SIZE = 50 * 1024 * 1024   # 50 MB
import tempfile
FILE_UPLOAD_TEMP_DIR = tempfile.gettempdir()
# =========================
# SEGURANÇA (produção)
# =========================
CSRF_TRUSTED_ORIGINS = [
    "https://*.replit.dev",
    "https://*.repl.co",
]

if not DEBUG:
    CSRF_TRUSTED_ORIGINS += [
        "https://seu-dominio.com",
    ]

    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True