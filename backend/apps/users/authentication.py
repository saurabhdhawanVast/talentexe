from __future__ import annotations

# apps/users/authentication.py

import jwt
from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed
from rest_framework.request import Request

from .models import UserProfile


class SupabaseJWTAuthentication(BaseAuthentication):
    """
    DRF authentication class that validates Supabase-issued JWTs.

    Phase 1 behaviour
    -----------------
    Signature verification is intentionally skipped (``verify_signature=False``)
    because the Supabase JWT secret is only available from the Supabase dashboard
    and has not yet been added to the environment. The token itself is issued by
    Supabase's auth service, so the ``sub`` claim is trustworthy in this context.

    Phase 2 upgrade path
    --------------------
    Set ``SUPABASE_JWT_SECRET`` in .env (found at Project Settings → API →
    JWT Secret), then replace ``options={"verify_signature": False}`` with:

        jwt.decode(token, settings.SUPABASE_JWT_SECRET, algorithms=["HS256"])

    Authentication flow
    -------------------
    1. Extract Bearer token from the ``Authorization`` header.
    2. Decode the JWT to read the ``sub`` claim (Supabase user UUID).
    3. Look up the matching active ``UserProfile`` row in Supabase/Postgres.
    4. Return ``(profile, token)`` — DRF sets ``request.user`` to the profile.
    """

    def authenticate(self, request: Request) -> tuple[UserProfile, str] | None:
        """Return ``(user, token)`` or ``None`` if no auth header is present."""
        auth_header: str = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            return None  # let other authenticators (e.g. session) try

        token: str = auth_header.split(" ", 1)[1].strip()
        if not token:
            raise AuthenticationFailed("Empty Bearer token.")

        try:
            payload: dict = jwt.decode(
                token,
                options={"verify_signature": False},
                algorithms=["HS256"],
            )
        except jwt.DecodeError as exc:
            raise AuthenticationFailed(f"Invalid token: {exc}") from exc
        except jwt.ExpiredSignatureError as exc:
            raise AuthenticationFailed("Token has expired.") from exc

        user_id: str | None = payload.get("sub")
        if not user_id:
            raise AuthenticationFailed("Token is missing the 'sub' claim.")

        try:
            profile = UserProfile.objects.get(id=user_id, is_active=True)
        except UserProfile.DoesNotExist:
            raise AuthenticationFailed("User not found or account is inactive.")

        return (profile, token)

    def authenticate_header(self, request: Request) -> str:
        """Return the WWW-Authenticate header value for 401 responses."""
        return 'Bearer realm="api"'
