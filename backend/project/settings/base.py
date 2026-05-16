from __future__ import annotations

# project/settings/base.py

from pathlib import Path
import environ

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent.parent.parent

# ---------------------------------------------------------------------------
# Environment
# ---------------------------------------------------------------------------
env = environ.Env(
    DJANGO_DEBUG=(bool, False),
    DJANGO_ALLOWED_HOSTS=(list, ["localhost", "127.0.0.1"]),
    CORS_ALLOWED_ORIGINS=(list, ["http://localhost:3000"]),
)
environ.Env.read_env(BASE_DIR / ".env")

# ---------------------------------------------------------------------------
# Security
# ---------------------------------------------------------------------------
SECRET_KEY = env("DJANGO_SECRET_KEY")
DEBUG = env("DJANGO_DEBUG")
ALLOWED_HOSTS: list[str] = env("DJANGO_ALLOWED_HOSTS")

# ---------------------------------------------------------------------------
# Application definition
# ---------------------------------------------------------------------------
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.postgres",
    # Third-party
    "rest_framework",
    "corsheaders",
    # Internal
    "apps.users",
    "apps.auth_ext",
    "apps.profiles",
    "apps.reviews",
    "apps.dashboard",
    "apps.ai_integration",
]

MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",  # must be before CommonMiddleware
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "project.urls"

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

WSGI_APPLICATION = "project.wsgi.application"

# ---------------------------------------------------------------------------
# Database — Supabase PostgreSQL via DATABASE_URL
# ---------------------------------------------------------------------------
DATABASES = {
    "default": env.db("DATABASE_URL"),
}
DATABASES["default"]["ENGINE"] = "django.db.backends.postgresql"
# Supabase pooler runs in transaction mode — server-side cursors don't survive
# across transactions, so we disable them entirely.
DATABASES["default"]["DISABLE_SERVER_SIDE_CURSORS"] = True

# ---------------------------------------------------------------------------
# Authentication
# ---------------------------------------------------------------------------
AUTH_USER_MODEL = "auth.User"  # Django built-in, used for superuser/admin only

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# ---------------------------------------------------------------------------
# Django REST Framework
# ---------------------------------------------------------------------------
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "apps.users.authentication.SupabaseJWTAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
    "DEFAULT_RENDERER_CLASSES": [
        "rest_framework.renderers.JSONRenderer",
    ],
    "EXCEPTION_HANDLER": "rest_framework.views.exception_handler",
}

# ---------------------------------------------------------------------------
# CORS
# ---------------------------------------------------------------------------
CORS_ALLOWED_ORIGINS: list[str] = env("CORS_ALLOWED_ORIGINS")
CORS_ALLOW_CREDENTIALS = True

# ---------------------------------------------------------------------------
# Internationalisation
# ---------------------------------------------------------------------------
LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

# ---------------------------------------------------------------------------
# Static files
# ---------------------------------------------------------------------------
STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

# ---------------------------------------------------------------------------
# Primary key type
# ---------------------------------------------------------------------------
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# ---------------------------------------------------------------------------
# Supabase client config (used by services.py)
# ---------------------------------------------------------------------------
SUPABASE_URL: str = env("SUPABASE_URL")
SUPABASE_SERVICE_ROLE_KEY: str = env("SUPABASE_SERVICE_ROLE_KEY", default="")
SUPABASE_ANON_KEY: str = env("SUPABASE_ANON_KEY", default="")
SUPABASE_STORAGE_BUCKET_RESUMES: str = env("SUPABASE_STORAGE_BUCKET_RESUMES", default="resumes")
SUPABASE_STORAGE_BUCKET_AVATARS: str = env("SUPABASE_STORAGE_BUCKET_AVATARS", default="avatars")

# ---------------------------------------------------------------------------
# Frontend URL (used in emails, password reset links, etc.)
# ---------------------------------------------------------------------------
FRONTEND_URL: str = env("FRONTEND_URL", default="http://localhost:3000")

# ---------------------------------------------------------------------------
# Ollama (local LLM for resume extraction)
# ---------------------------------------------------------------------------
OLLAMA_BASE_URL: str = env("OLLAMA_BASE_URL", default="http://localhost:11434")
OLLAMA_LLM_MODEL: str = env("OLLAMA_LLM_MODEL", default="llama3.2:3b")

# ---------------------------------------------------------------------------
# Email — Brevo SMTP
# ---------------------------------------------------------------------------
EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
EMAIL_HOST: str = env("BREVO_SMTP_HOST", default="smtp-relay.brevo.com")
EMAIL_PORT: int = env.int("BREVO_SMTP_PORT", default=587)
EMAIL_HOST_USER: str = env("BREVO_SMTP_USER", default="")
EMAIL_HOST_PASSWORD: str = env("BREVO_SMTP_PASSWORD", default="")
EMAIL_USE_TLS = True
DEFAULT_FROM_EMAIL: str = (
    env("EMAIL_FROM_NAME", default="TalentExe")
    + " <"
    + env("EMAIL_FROM", default="noreply@talentexe.com")
    + ">"
)
