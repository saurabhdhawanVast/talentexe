from __future__ import annotations

# apps/dashboard/urls.py

from django.urls import path

from .views import DashboardStatsView

urlpatterns = [
    path("stats/", DashboardStatsView.as_view(), name="dashboard-stats"),
]
