from __future__ import annotations

# apps/users/urls.py

from django.urls import path

from .views import (
    AvatarUploadView,
    BulkUploadView,
    DisableUserView,
    MeView,
    ResendInviteView,
    UserDetailView,
    UserListCreateView,
)

urlpatterns = [
    path("auth/me/", MeView.as_view(), name="me"),
    path("users/", UserListCreateView.as_view(), name="user-list-create"),
    path("users/bulk-upload/", BulkUploadView.as_view(), name="user-bulk-upload"),
    path("users/<uuid:pk>/", UserDetailView.as_view(), name="user-detail"),
    path("users/<uuid:pk>/disable/", DisableUserView.as_view(), name="user-disable"),
    path(
        "users/<uuid:pk>/resend-invite/",
        ResendInviteView.as_view(),
        name="user-resend-invite",
    ),
    path(
        "users/<uuid:pk>/avatar/",
        AvatarUploadView.as_view(),
        name="user-avatar-upload",
    ),
]
