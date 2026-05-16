from __future__ import annotations

# project/settings/prod.py

from .base import *  # noqa: F401, F403

DEBUG = False

# In production, ALLOWED_HOSTS must be set explicitly via DJANGO_ALLOWED_HOSTS env var
# CORS_ALLOWED_ORIGINS must be set via CORS_ALLOWED_ORIGINS env var

# Security hardening for production
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = "DENY"
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
