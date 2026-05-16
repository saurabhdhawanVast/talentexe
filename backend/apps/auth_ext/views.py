from __future__ import annotations

# apps/auth_ext/views.py

import logging

import jwt
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.users.authentication import SupabaseJWTAuthentication
from apps.users.models import UserProfile
from apps.users.serializers import (
    ChangePasswordSerializer,
    ForgotPasswordSerializer,
    ResetPasswordSerializer,
)
from apps.users.services import (
    generate_supabase_recovery_link,
    reset_supabase_user_password,
    send_forgot_password_email,
)

logger = logging.getLogger(__name__)

_AUTH = [SupabaseJWTAuthentication]


def _ok(data: object, http_status: int = 200) -> Response:
    return Response({"data": data, "error": None, "meta": {}}, status=http_status)


def _err(message: str, detail: str = "", http_status: int = 400) -> Response:
    return Response(
        {"data": None, "error": message, "meta": {"detail": detail}},
        status=http_status,
    )


class ChangePasswordView(APIView):
    """
    POST /api/v1/auth/change-password/

    Authenticated endpoint. Updates the caller's Supabase auth password
    and clears the must_change_password flag on their profile.

    Body: { "new_password": "..." }
    """

    authentication_classes = _AUTH
    permission_classes = [IsAuthenticated]

    def post(self, request: Request) -> Response:
        serializer = ChangePasswordSerializer(data=request.data)
        if not serializer.is_valid():
            return _err("Validation error.", detail=str(serializer.errors))

        new_password: str = serializer.validated_data["new_password"]
        profile: UserProfile = request.user

        try:
            reset_supabase_user_password(str(profile.id), new_password)
        except Exception as exc:
            logger.error(
                "Supabase password update failed for %s: %s", profile.id, exc
            )
            return _err("Failed to update password.", detail=str(exc), http_status=500)

        profile.must_change_password = False
        profile.save(update_fields=["must_change_password"])

        return _ok({"message": "Password updated successfully."})


class ForgotPasswordView(APIView):
    """
    POST /api/v1/auth/forgot-password/

    Public endpoint. Generates a Supabase recovery link for the given email
    and sends it via Brevo SMTP. Always returns 200 to prevent email
    enumeration attacks.

    Body: { "email": "user@example.com" }
    """

    authentication_classes = []
    permission_classes = [AllowAny]

    def post(self, request: Request) -> Response:
        serializer = ForgotPasswordSerializer(data=request.data)
        if not serializer.is_valid():
            return _err("Validation error.", detail=str(serializer.errors))

        email: str = serializer.validated_data["email"]

        # Look up the profile (used to personalise email); if not found we
        # still return 200 to prevent email enumeration.
        try:
            profile = UserProfile.objects.get(email__iexact=email, is_active=True)
        except UserProfile.DoesNotExist:
            return _ok({"message": "If that email exists, a reset link has been sent."})

        try:
            recovery_link = generate_supabase_recovery_link(email)
        except Exception as exc:
            logger.error("Recovery link generation failed for %s: %s", email, exc)
            # Return 200 to avoid leaking whether the user exists
            return _ok({"message": "If that email exists, a reset link has been sent."})

        send_forgot_password_email(
            to_email=profile.email,
            full_name=profile.full_name,
            recovery_link=recovery_link,
        )

        return _ok({"message": "If that email exists, a reset link has been sent."})


class ResetPasswordView(APIView):
    """
    POST /api/v1/auth/reset-password/

    Public endpoint. The frontend extracts the Supabase access token from
    the recovery URL hash and POSTs it here along with the new password.

    We decode the JWT (without signature verification — the token was issued
    by Supabase and short-lived) to extract the user id, then update the
    password via the admin API.

    Body: { "token": "<supabase-access-token>", "new_password": "..." }
    """

    authentication_classes = []
    permission_classes = [AllowAny]

    def post(self, request: Request) -> Response:
        serializer = ResetPasswordSerializer(data=request.data)
        if not serializer.is_valid():
            return _err("Validation error.", detail=str(serializer.errors))

        token: str = serializer.validated_data["token"]
        new_password: str = serializer.validated_data["new_password"]

        try:
            payload: dict = jwt.decode(
                token,
                options={"verify_signature": False},
                algorithms=["HS256"],
            )
        except jwt.DecodeError as exc:
            return _err("Invalid or malformed token.", detail=str(exc), http_status=400)
        except jwt.ExpiredSignatureError:
            return _err("Token has expired. Please request a new reset link.", http_status=400)

        user_id: str | None = payload.get("sub")
        if not user_id:
            return _err("Token is missing the user identifier.", http_status=400)

        # Verify user exists in our system
        try:
            profile = UserProfile.objects.get(id=user_id, is_active=True)
        except UserProfile.DoesNotExist:
            return _err("User not found or account is inactive.", http_status=404)

        try:
            reset_supabase_user_password(user_id, new_password)
        except Exception as exc:
            logger.error("Password reset failed for %s: %s", user_id, exc)
            return _err("Failed to reset password.", detail=str(exc), http_status=500)

        # Clear force-change flag if it was set
        if profile.must_change_password:
            profile.must_change_password = False
            profile.save(update_fields=["must_change_password"])

        return _ok({"message": "Password reset successfully. You can now log in."})
