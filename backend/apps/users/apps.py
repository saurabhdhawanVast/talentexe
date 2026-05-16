from __future__ import annotations

# apps/users/apps.py

from django.apps import AppConfig


class UsersConfig(AppConfig):
    """AppConfig for the users domain."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.users"
    verbose_name = "Users"
