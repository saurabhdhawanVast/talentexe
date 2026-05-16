from __future__ import annotations

# apps/users/views.py

import io
import json
import logging

from django.db import transaction
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from .authentication import SupabaseJWTAuthentication
from .models import UserProfile
from .permissions import IsHR
from .serializers import (
    BulkUploadSerializer,
    UserCreateSerializer,
    UserListSerializer,
    UserProfileSerializer,
    UserUpdateSerializer,
)
from .services import (
    create_supabase_user,
    delete_supabase_user,
    generate_temp_password,
    reset_supabase_user_password,
    send_welcome_email,
    update_supabase_user,
)

logger = logging.getLogger(__name__)

_AUTH = [SupabaseJWTAuthentication]


def _ok(data: object, meta: dict | None = None, http_status: int = 200) -> Response:
    return Response(
        {"data": data, "error": None, "meta": meta or {}}, status=http_status
    )


def _err(message: str, detail: str = "", http_status: int = 400) -> Response:
    return Response(
        {"data": None, "error": message, "meta": {"detail": detail}},
        status=http_status,
    )


# ---------------------------------------------------------------------------
# Auth: Me
# ---------------------------------------------------------------------------


class MeView(APIView):
    """
    GET /api/v1/auth/me/

    Returns the authenticated user's full profile.
    """

    authentication_classes = _AUTH
    permission_classes = [IsAuthenticated]

    def get(self, request: Request) -> Response:
        profile: UserProfile = request.user
        serializer = UserProfileSerializer(profile)
        return _ok(serializer.data)


# ---------------------------------------------------------------------------
# Users: List + Create
# ---------------------------------------------------------------------------


class UserListCreateView(APIView):
    """
    GET  /api/v1/users/   — HR: paginated, filtered list of all users.
    POST /api/v1/users/   — HR: create a single user and send welcome email.
    """

    authentication_classes = _AUTH
    permission_classes = [IsAuthenticated, IsHR]

    def get(self, request: Request) -> Response:
        qs = UserProfile.objects.filter(role='employee').order_by("-created_at")

        # --- filters ---
        search = request.query_params.get("search", "").strip()
        if search:
            qs = qs.filter(email__icontains=search) | qs.filter(full_name__icontains=search)

        status = request.query_params.get("status", "").strip()
        if status and status != "all":
            qs = qs.filter(profile_status=status)

        for field in ("designation", "department", "location"):
            val = request.query_params.get(field, "").strip()
            if val:
                qs = qs.filter(**{f"{field}__icontains": val})

        exp_min = request.query_params.get("exp_min", "").strip()
        if exp_min:
            try:
                qs = qs.filter(experience_years__gte=float(exp_min))
            except ValueError:
                pass

        exp_max = request.query_params.get("exp_max", "").strip()
        if exp_max:
            try:
                qs = qs.filter(experience_years__lte=float(exp_max))
            except ValueError:
                pass

        # --- pagination ---
        try:
            page = max(1, int(request.query_params.get("page", 1)))
            page_size = min(100, max(1, int(request.query_params.get("page_size", 20))))
        except ValueError:
            page, page_size = 1, 20

        total = qs.count()
        start = (page - 1) * page_size
        users = qs[start : start + page_size]

        serializer = UserListSerializer(users, many=True)
        return _ok(
            serializer.data,
            meta={
                "total": total,
                "page": page,
                "page_size": page_size,
                "pages": (total + page_size - 1) // page_size,
            },
        )

    def post(self, request: Request) -> Response:
        serializer = UserCreateSerializer(data=request.data)
        if not serializer.is_valid():
            return _err("Validation error.", detail=str(serializer.errors), http_status=400)

        data = serializer.validated_data

        if data.get("role") == "hr":
            return _err("HR cannot create another HR account.", http_status=403)

        try:
            user_id, temp_password = create_supabase_user(
                email=data["email"],
                full_name=data["full_name"],
                role=data["role"],
            )
        except Exception as exc:
            logger.error("Supabase user creation failed: %s", exc)
            return _err("Failed to create auth user.", detail=str(exc), http_status=500)

        # Send email before persisting anything — if it fails, roll back Supabase
        # and return an error so no partial state is left behind.
        try:
            send_welcome_email(
                to_email=data["email"],
                full_name=data["full_name"],
                temp_password=temp_password,
                role=data["role"],
            )
        except Exception as exc:
            try:
                delete_supabase_user(user_id)
            except Exception:
                pass
            logger.error("Welcome email failed, rolling back user creation: %s", exc)
            return _err(
                "Failed to send welcome email. User was not created.",
                detail=str(exc),
                http_status=500,
            )

        optional_fields = {
            k: data[k]
            for k in ("phone", "designation", "department", "experience_years", "location")
            if k in data and data[k] not in (None, "")
        }

        try:
            with transaction.atomic():
                profile = UserProfile.objects.create(
                    id=user_id,
                    email=data["email"],
                    full_name=data["full_name"],
                    role=data["role"],
                    is_active=True,
                    must_change_password=True,
                    profile_status="incomplete",
                    created_by=request.user,
                    **optional_fields,
                )
        except Exception as exc:
            try:
                delete_supabase_user(user_id)
            except Exception:
                pass
            logger.error("Profile creation failed: %s", exc)
            return _err("Failed to create user profile.", detail=str(exc), http_status=500)

        return _ok(UserProfileSerializer(profile).data, http_status=201)


# ---------------------------------------------------------------------------
# Users: Detail, Update, Delete
# ---------------------------------------------------------------------------


class UserDetailView(APIView):
    """
    GET    /api/v1/users/{pk}/   — HR: retrieve full profile.
    PATCH  /api/v1/users/{pk}/   — HR: update mutable fields.
    DELETE /api/v1/users/{pk}/   — HR: delete user from auth + DB.
    """

    authentication_classes = _AUTH
    permission_classes = [IsAuthenticated, IsHR]

    def _get_profile(self, pk: str) -> UserProfile | None:
        try:
            return UserProfile.objects.get(id=pk)
        except UserProfile.DoesNotExist:
            return None

    def get(self, request: Request, pk: str) -> Response:
        profile = self._get_profile(pk)
        if profile is None:
            return _err("User not found.", http_status=404)
        return _ok(UserProfileSerializer(profile).data)

    def patch(self, request: Request, pk: str) -> Response:
        profile = self._get_profile(pk)
        if profile is None:
            return _err("User not found.", http_status=404)

        serializer = UserUpdateSerializer(profile, data=request.data, partial=True)
        if not serializer.is_valid():
            return _err("Validation error.", detail=str(serializer.errors))

        serializer.save()
        return _ok(UserProfileSerializer(profile).data)

    def delete(self, request: Request, pk: str) -> Response:
        profile = self._get_profile(pk)
        if profile is None:
            return _err("User not found.", http_status=404)

        try:
            delete_supabase_user(str(profile.id))
        except Exception as exc:
            logger.error("Supabase delete failed for %s: %s", pk, exc)
            return _err("Failed to delete auth user.", detail=str(exc), http_status=500)

        profile.delete()
        return _ok({"deleted": str(pk)})


# ---------------------------------------------------------------------------
# Users: Disable
# ---------------------------------------------------------------------------


class DisableUserView(APIView):
    """
    POST /api/v1/users/{pk}/disable/

    Toggle is_active on the UserProfile and ban/unban the Supabase auth user.
    HR only.
    """

    authentication_classes = _AUTH
    permission_classes = [IsAuthenticated, IsHR]

    def post(self, request: Request, pk: str) -> Response:
        try:
            profile = UserProfile.objects.get(id=pk)
        except UserProfile.DoesNotExist:
            return _err("User not found.", http_status=404)

        # Toggle
        new_active = not profile.is_active
        try:
            update_supabase_user(str(profile.id), ban=not new_active)
        except Exception as exc:
            logger.error("Supabase ban update failed for %s: %s", pk, exc)
            return _err("Failed to update auth status.", detail=str(exc), http_status=500)

        profile.is_active = new_active
        profile.save(update_fields=["is_active"])

        return _ok({"id": str(pk), "is_active": new_active})


# ---------------------------------------------------------------------------
# Users: Resend Invite
# ---------------------------------------------------------------------------


class ResendInviteView(APIView):
    """
    POST /api/v1/users/{pk}/resend-invite/

    Generate a new temporary password, update it in Supabase, and re-send
    the welcome email. HR only.
    """

    authentication_classes = _AUTH
    permission_classes = [IsAuthenticated, IsHR]

    def post(self, request: Request, pk: str) -> Response:
        try:
            profile = UserProfile.objects.get(id=pk)
        except UserProfile.DoesNotExist:
            return _err("User not found.", http_status=404)

        new_password = generate_temp_password()
        try:
            reset_supabase_user_password(str(profile.id), new_password)
        except Exception as exc:
            logger.error("Password reset failed for %s: %s", pk, exc)
            return _err("Failed to reset password.", detail=str(exc), http_status=500)

        profile.must_change_password = True
        profile.save(update_fields=["must_change_password"])

        send_welcome_email(
            to_email=profile.email,
            full_name=profile.full_name,
            temp_password=new_password,
            role=profile.role,
        )

        return _ok({"message": "Invite resent successfully."})


# ---------------------------------------------------------------------------
# Users: Bulk Upload
# ---------------------------------------------------------------------------


class BulkUploadView(APIView):
    """
    POST /api/v1/users/bulk-upload/

    Parse an Excel or JSON file containing user rows. For each valid row,
    create a Supabase Auth user and a UserProfile, then send a welcome email.
    Returns a summary of successes and per-row errors.

    HR only.
    """

    authentication_classes = _AUTH
    permission_classes = [IsAuthenticated, IsHR]

    def post(self, request: Request) -> Response:
        serializer = BulkUploadSerializer(data=request.data)
        if not serializer.is_valid():
            return _err("Validation error.", detail=str(serializer.errors))

        uploaded_file = serializer.validated_data["file"]
        file_name: str = uploaded_file.name or ""
        file_bytes: bytes = uploaded_file.read()

        rows: list[dict] = []

        if file_name.endswith(".json"):
            try:
                rows = json.loads(file_bytes.decode("utf-8"))
                if not isinstance(rows, list):
                    return _err("JSON file must contain a list of user objects.")
            except (json.JSONDecodeError, UnicodeDecodeError) as exc:
                return _err("Invalid JSON file.", detail=str(exc))

        elif file_name.endswith(".xlsx"):
            try:
                import openpyxl  # noqa: PLC0415

                wb = openpyxl.load_workbook(io.BytesIO(file_bytes))
                ws = wb.active
                headers: list[str] = []
                for i, row in enumerate(ws.iter_rows(values_only=True)):
                    if i == 0:
                        headers = [str(c).strip() if c else "" for c in row]
                    else:
                        if all(c is None for c in row):
                            continue
                        rows.append(
                            {
                                headers[j]: (str(row[j]).strip() if row[j] is not None else "")
                                for j in range(len(headers))
                            }
                        )
            except Exception as exc:
                return _err("Failed to parse Excel file.", detail=str(exc))
        else:
            return _err("Unsupported file format. Use .xlsx or .json.")

        created: list[str] = []
        errors: list[dict] = []

        for idx, row in enumerate(rows, start=1):
            row_label = row.get("email") or f"row {idx}"
            row_serializer = UserCreateSerializer(data=row)
            if not row_serializer.is_valid():
                errors.append({"row": row_label, "errors": row_serializer.errors})
                continue

            data = row_serializer.validated_data
            try:
                user_id, temp_password = create_supabase_user(
                    email=data["email"],
                    full_name=data["full_name"],
                    role=data["role"],
                )
            except Exception as exc:
                errors.append({"row": row_label, "errors": {"auth": str(exc)}})
                continue

            optional_fields = {
                k: data[k]
                for k in (
                    "phone",
                    "designation",
                    "department",
                    "experience_years",
                    "location",
                )
                if k in data and data[k] not in (None, "")
            }

            try:
                profile = UserProfile.objects.create(
                    id=user_id,
                    email=data["email"],
                    full_name=data["full_name"],
                    role=data["role"],
                    is_active=True,
                    must_change_password=True,
                    profile_status="incomplete",
                    created_by=request.user,
                    **optional_fields,
                )
                send_welcome_email(
                    to_email=profile.email,
                    full_name=profile.full_name,
                    temp_password=temp_password,
                    role=profile.role,
                )
                created.append(data["email"])
            except Exception as exc:
                try:
                    delete_supabase_user(user_id)
                except Exception:
                    pass
                errors.append({"row": row_label, "errors": {"db": str(exc)}})

        return _ok(
            {
                "created_count": len(created),
                "error_count": len(errors),
                "created": created,
                "errors": errors,
            },
            http_status=201 if created else 200,
        )


# ---------------------------------------------------------------------------
# Users: Avatar Upload
# ---------------------------------------------------------------------------


class AvatarUploadView(APIView):
    """
    POST /api/v1/users/{pk}/avatar/
    Multipart: field name "avatar" (image file)
    HR or the profile owner can upload.
    """

    authentication_classes = _AUTH
    permission_classes = [IsAuthenticated]

    def post(self, request: Request, pk: str) -> Response:
        # Only allow HR or the profile owner
        profile = request.user
        if str(profile.id) != str(pk) and profile.role != 'hr':
            return _err("Permission denied.", http_status=403)

        file = request.FILES.get('avatar')
        if not file:
            return _err("No file provided.", http_status=400)

        allowed_types = {'image/jpeg', 'image/png', 'image/webp'}
        if file.content_type not in allowed_types:
            return _err("Only JPG, PNG, and WebP images are supported.", http_status=400)

        if file.size > 2 * 1024 * 1024:
            return _err("Image must be smaller than 2MB.", http_status=400)

        try:
            target = UserProfile.objects.get(id=pk)
        except UserProfile.DoesNotExist:
            return _err("User not found.", http_status=404)

        import os
        ext = os.path.splitext(file.name)[1] or '.jpg'
        storage_path = f"{pk}/avatar{ext}"
        file_bytes = file.read()

        from django.conf import settings as django_settings
        from supabase import create_client as supabase_create_client

        supabase_client = supabase_create_client(
            django_settings.SUPABASE_URL,
            django_settings.SUPABASE_SERVICE_ROLE_KEY,
        )

        bucket = supabase_client.storage.from_('avatars')

        # Try update first, fall back to upload if not found
        try:
            bucket.update(storage_path, file_bytes, {'content-type': file.content_type})
        except Exception:
            try:
                bucket.upload(storage_path, file_bytes, {'content-type': file.content_type})
            except Exception as exc:
                logger.error("Supabase storage upload failed: %s", exc)
                return _err("Failed to upload image.", detail=str(exc), http_status=500)

        public_url = supabase_client.storage.from_('avatars').get_public_url(storage_path)

        target.avatar_url = public_url
        target.save(update_fields=['avatar_url'])

        return _ok({'avatar_url': public_url})
