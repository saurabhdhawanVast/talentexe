from __future__ import annotations

# apps/auth_ext/apps.py

from django.apps import AppConfig


class AuthExtConfig(AppConfig):
    """AppConfig for the auth_ext domain (password change / reset flows)."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.auth_ext"
    verbose_name = "Auth Extensions"
