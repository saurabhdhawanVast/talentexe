from __future__ import annotations

# apps/users/serializers.py

from rest_framework import serializers

from .models import UserProfile


class UserProfileSerializer(serializers.ModelSerializer):
    """
    Full read serializer for the UserProfile model.

    Returned by MeView and UserDetailView. Exposes all fields that are
    safe to return to the authenticated user (no password data).
    """

    id = serializers.UUIDField(read_only=True)
    created_by = serializers.PrimaryKeyRelatedField(read_only=True)

    class Meta:
        model = UserProfile
        fields = [
            "id",
            "email",
            "full_name",
            "role",
            "is_active",
            "phone",
            "designation",
            "department",
            "experience_years",
            "location",
            "avatar_url",
            "must_change_password",
            "profile_status",
            "created_by",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields


class UserListSerializer(serializers.ModelSerializer):
    """
    Condensed serializer used in list endpoints to reduce payload size.
    Exposes `status` (mapped from profile_status) so the frontend EmployeeListItem type is satisfied.
    """

    id = serializers.UUIDField(read_only=True)
    status = serializers.CharField(source="profile_status", read_only=True)

    class Meta:
        model = UserProfile
        fields = [
            "id",
            "email",
            "full_name",
            "role",
            "is_active",
            "designation",
            "department",
            "experience_years",
            "location",
            "profile_status",
            "status",
        ]
        read_only_fields = fields


class UserCreateSerializer(serializers.Serializer):
    """
    Input serializer for POST /api/v1/users/.

    Validates the payload before creating a Supabase Auth user and a
    corresponding UserProfile row.
    """

    email = serializers.EmailField()
    full_name = serializers.CharField(max_length=255)
    role = serializers.ChoiceField(choices=["hr", "employee"])
    phone = serializers.CharField(max_length=20, required=False, allow_blank=True)
    designation = serializers.CharField(
        max_length=255, required=False, allow_blank=True
    )
    department = serializers.CharField(
        max_length=255, required=False, allow_blank=True
    )
    experience_years = serializers.DecimalField(
        max_digits=4, decimal_places=1, required=False, allow_null=True
    )
    location = serializers.CharField(
        max_length=255, required=False, allow_blank=True
    )

    def validate_email(self, value: str) -> str:
        """Reject duplicate emails before hitting the database."""
        if UserProfile.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError(
                "A user with this email already exists."
            )
        return value.lower()


class UserUpdateSerializer(serializers.ModelSerializer):
    """
    Input serializer for PATCH /api/v1/users/{pk}/.

    Only mutable profile fields are exposed. Email and role cannot be
    changed after creation to avoid Supabase Auth de-sync.
    """

    class Meta:
        model = UserProfile
        fields = [
            "full_name",
            "phone",
            "designation",
            "department",
            "experience_years",
            "location",
            "avatar_url",
        ]


class BulkUploadSerializer(serializers.Serializer):
    """
    Input serializer for POST /api/v1/users/bulk-upload/.

    Accepts either an Excel (.xlsx) or JSON (.json) file containing
    multiple user records. Maximum file size is 5 MB.
    """

    file = serializers.FileField()

    def validate_file(self, value):  # type: ignore[override]
        max_size = 5 * 1024 * 1024  # 5 MB
        if value.size > max_size:
            raise serializers.ValidationError("File must be smaller than 5 MB.")
        allowed_types = {
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            "application/json",
            "text/json",
        }
        content_type = value.content_type or ""
        name = value.name or ""
        if content_type not in allowed_types and not (
            name.endswith(".xlsx") or name.endswith(".json")
        ):
            raise serializers.ValidationError(
                "Only .xlsx and .json files are supported."
            )
        return value


class RejectReviewSerializer(serializers.Serializer):
    """Input serializer for POST /api/v1/reviews/{pk}/reject/."""

    comment = serializers.CharField(min_length=1)


class ChangePasswordSerializer(serializers.Serializer):
    """Input serializer for POST /api/v1/auth/change-password/."""

    new_password = serializers.CharField(min_length=8)


class ForgotPasswordSerializer(serializers.Serializer):
    """Input serializer for POST /api/v1/auth/forgot-password/."""

    email = serializers.EmailField()


class ResetPasswordSerializer(serializers.Serializer):
    """
    Input serializer for POST /api/v1/auth/reset-password/.

    `token` is the Supabase access token extracted from the recovery URL
    hash by the frontend and POSTed here. We decode it to get the user id.
    """

    token = serializers.CharField()
    new_password = serializers.CharField(min_length=8)
