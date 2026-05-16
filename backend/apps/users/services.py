from __future__ import annotations

# apps/users/services.py

import logging
import os
import secrets
import string

from django.conf import settings
from django.core.mail import send_mail

from supabase import Client, create_client

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Supabase client
# ---------------------------------------------------------------------------


def get_supabase_admin_client() -> Client:
    """Return a Supabase client authenticated with the service role key."""
    url: str | None = os.environ.get("SUPABASE_URL")
    key: str | None = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
    if not url or not key:
        raise ValueError("SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY must be set.")
    return create_client(url, key)


# ---------------------------------------------------------------------------
# Password utilities
# ---------------------------------------------------------------------------


def generate_temp_password(length: int = 12) -> str:
    """
    Generate a cryptographically random temporary password.

    The password always contains at least one uppercase letter, one digit,
    and one symbol to satisfy most password-strength requirements.
    """
    alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
    while True:
        password = "".join(secrets.choice(alphabet) for _ in range(length))
        has_upper = any(c.isupper() for c in password)
        has_digit = any(c.isdigit() for c in password)
        has_symbol = any(c in "!@#$%^&*" for c in password)
        if has_upper and has_digit and has_symbol:
            return password


# ---------------------------------------------------------------------------
# Supabase Auth operations
# ---------------------------------------------------------------------------


def create_supabase_user(
    email: str, full_name: str, role: str
) -> tuple[str, str]:
    """
    Create a Supabase Auth user and return ``(user_id, temp_password)``.

    The caller is responsible for storing or immediately emailing the
    temp_password — it is not stored anywhere after this function returns.
    """
    client = get_supabase_admin_client()
    temp_password = generate_temp_password()
    response = client.auth.admin.create_user(
        {
            "email": email,
            "password": temp_password,
            "email_confirm": True,
            "user_metadata": {"full_name": full_name, "role": role},
        }
    )
    return str(response.user.id), temp_password


def get_supabase_user_by_email(email: str):
    """Return the Supabase Auth user for the given email, or None."""
    client = get_supabase_admin_client()
    response = client.auth.admin.list_users()
    for user in response:
        if user.email == email:
            return user
    return None


def delete_supabase_user(user_id: str) -> None:
    """Delete a user from Supabase Auth by UUID."""
    client = get_supabase_admin_client()
    client.auth.admin.delete_user(user_id)


def update_supabase_user(user_id: str, *, ban: bool = False) -> None:
    """Update a Supabase Auth user (e.g. ban/unban to mirror is_active)."""
    client = get_supabase_admin_client()
    client.auth.admin.update_user_by_id(
        user_id,
        {"ban_duration": "876600h" if ban else "none"},
    )


def reset_supabase_user_password(user_id: str, new_password: str) -> None:
    """
    Update a Supabase Auth user's password via the admin API.

    Used by ChangePasswordView and ResetPasswordView.
    """
    client = get_supabase_admin_client()
    client.auth.admin.update_user_by_id(
        user_id,
        {"password": new_password},
    )


def generate_supabase_recovery_link(email: str) -> str:
    """
    Generate a Supabase password-recovery magic link and return the raw URL.

    Supabase will send the user to ``redirect_to`` after they click the link.
    The frontend must handle the ``/reset-password`` route and extract the
    access token from the URL hash to complete the reset.
    """
    client = get_supabase_admin_client()
    redirect_to = f"{settings.FRONTEND_URL}/reset-password"
    response = client.auth.admin.generate_link(
        {
            "type": "recovery",
            "email": email,
            "options": {"redirect_to": redirect_to},
        }
    )
    # response.properties.action_link contains the full recovery URL
    return response.properties.action_link


# ---------------------------------------------------------------------------
# Email notifications
# ---------------------------------------------------------------------------


def send_welcome_email(
    to_email: str, full_name: str, temp_password: str, role: str
) -> None:
    """
    Send a welcome / onboarding email with login credentials to a new user.

    The email includes the temporary password. The user is prompted to
    change it on first login (enforced by must_change_password flag).
    """
    role_label = "HR Administrator" if role == "hr" else "Employee"
    login_url = f"{settings.FRONTEND_URL}/login"
    subject = "Welcome to TalentExe — Your account is ready"
    message = (
        f"Hello {full_name},\n\n"
        f"Your TalentExe account has been created as a {role_label}.\n\n"
        f"Login URL : {login_url}\n"
        f"Email     : {to_email}\n"
        f"Password  : {temp_password}\n\n"
        "Please log in and change your password immediately. "
        "You will be prompted to do so on your first login.\n\n"
        "If you did not expect this email, please contact your HR department.\n\n"
        "Regards,\nTalentExe Team"
    )
    try:
        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[to_email],
            fail_silently=False,
        )
    except Exception as exc:
        logger.error("Failed to send welcome email to %s: %s", to_email, exc)


def send_approval_email(to_email: str, full_name: str) -> None:
    """Notify an employee that their profile has been approved by HR."""
    subject = "Your TalentExe profile has been approved"
    message = (
        f"Hello {full_name},\n\n"
        "Your profile has been reviewed and approved by HR. "
        "You can now view your approved profile on TalentExe.\n\n"
        f"Visit: {settings.FRONTEND_URL}/profile\n\n"
        "Regards,\nTalentExe Team"
    )
    try:
        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[to_email],
            fail_silently=False,
        )
    except Exception as exc:
        logger.error("Failed to send approval email to %s: %s", to_email, exc)


def send_rejection_email(to_email: str, full_name: str, comment: str) -> None:
    """Notify an employee that their profile review was rejected with a comment."""
    subject = "Your TalentExe profile needs attention"
    message = (
        f"Hello {full_name},\n\n"
        "Your profile has been reviewed by HR and requires changes before approval.\n\n"
        f"HR Comment: {comment}\n\n"
        "Please update your profile and re-submit for review.\n"
        f"Visit: {settings.FRONTEND_URL}/profile\n\n"
        "Regards,\nTalentExe Team"
    )
    try:
        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[to_email],
            fail_silently=False,
        )
    except Exception as exc:
        logger.error("Failed to send rejection email to %s: %s", to_email, exc)


def send_forgot_password_email(
    to_email: str, full_name: str, recovery_link: str
) -> None:
    """Send a password reset link to the user."""
    subject = "TalentExe — Password Reset Request"
    message = (
        f"Hello {full_name},\n\n"
        "We received a request to reset your TalentExe password.\n\n"
        "Click the link below to set a new password. "
        "This link expires in 1 hour.\n\n"
        f"{recovery_link}\n\n"
        "If you did not request a password reset, you can safely ignore this email.\n\n"
        "Regards,\nTalentExe Team"
    )
    try:
        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[to_email],
            fail_silently=False,
        )
    except Exception as exc:
        logger.error(
            "Failed to send forgot-password email to %s: %s", to_email, exc
        )
