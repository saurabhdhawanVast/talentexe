from __future__ import annotations

# apps/auth_ext/urls.py

from django.urls import path

from .views import ChangePasswordView, ForgotPasswordView, ResetPasswordView

urlpatterns = [
    path("change-password/", ChangePasswordView.as_view(), name="change-password"),
    path("forgot-password/", ForgotPasswordView.as_view(), name="forgot-password"),
    path("reset-password/", ResetPasswordView.as_view(), name="reset-password"),
]
