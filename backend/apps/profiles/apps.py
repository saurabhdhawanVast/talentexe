from __future__ import annotations

# apps/profiles/apps.py

from django.apps import AppConfig


class ProfilesConfig(AppConfig):
    """AppConfig for the profiles domain (employee profiles, resumes, PDF export)."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.profiles"
    verbose_name = "Profiles"
