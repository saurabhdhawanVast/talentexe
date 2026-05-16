from __future__ import annotations

# project/urls.py

from django.contrib import admin
from django.urls import include, path

from apps.profiles.views import SkillsMasterView

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/v1/", include("apps.users.urls")),
    path("api/v1/auth/", include("apps.auth_ext.urls")),
    path("api/v1/profiles/", include("apps.profiles.urls")),
    path("api/v1/reviews/", include("apps.reviews.urls")),
    path("api/v1/dashboard/", include("apps.dashboard.urls")),
    path("api/v1/ai/", include("apps.ai_integration.urls")),
    # Skills master catalogue — separate from profile sub-resources
    path("api/v1/skills/", SkillsMasterView.as_view(), name="skills-master"),
]
