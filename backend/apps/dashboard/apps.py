from __future__ import annotations

# apps/dashboard/apps.py

from django.apps import AppConfig


class DashboardConfig(AppConfig):
    """AppConfig for the dashboard domain (aggregate stats for HR)."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.dashboard"
    verbose_name = "Dashboard"
