from __future__ import annotations

# apps/reviews/apps.py

from django.apps import AppConfig


class ReviewsConfig(AppConfig):
    """AppConfig for the reviews domain (HR profile approval workflow)."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.reviews"
    verbose_name = "Reviews"
