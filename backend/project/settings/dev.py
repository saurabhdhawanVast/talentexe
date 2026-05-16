from __future__ import annotations

# project/settings/dev.py

from .base import *  # noqa: F401, F403

DEBUG = True

ALLOWED_HOSTS = ["localhost", "127.0.0.1"]

# Looser CORS in dev — allow all localhost ports
CORS_ALLOW_ALL_ORIGINS = False  # keep explicit list from base

# Django Debug Toolbar or other dev-only apps can be added here
# INSTALLED_APPS += ["debug_toolbar"]
