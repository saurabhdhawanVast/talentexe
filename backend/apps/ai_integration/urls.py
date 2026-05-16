from __future__ import annotations

# apps/ai_integration/urls.py

from django.urls import path

from .views import ExtractionStatusView, ExtractionTriggerView, LinkedinExtractionView

urlpatterns = [
    path(
        "extract/<uuid:resume_upload_id>/",
        ExtractionTriggerView.as_view(),
        name="ai-extract-trigger",
    ),
    path(
        "extractions/<uuid:profile_id>/",
        ExtractionStatusView.as_view(),
        name="ai-extraction-status",
    ),
    path(
        "extract-linkedin/",
        LinkedinExtractionView.as_view(),
        name="ai-extract-linkedin",
    ),
]
