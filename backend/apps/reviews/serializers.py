from __future__ import annotations

# apps/reviews/serializers.py

from rest_framework import serializers

from .models import ProfileReview


class ProfileReviewSerializer(serializers.ModelSerializer):
    """Read serializer for ProfileReview, including denormalized employee info."""

    employee_name = serializers.SerializerMethodField()
    employee_email = serializers.SerializerMethodField()
    employee_designation = serializers.SerializerMethodField()
    employee_department = serializers.SerializerMethodField()
    reviewed_by_name = serializers.SerializerMethodField()

    class Meta:
        model = ProfileReview
        fields = [
            "id",
            "profile_id",
            "employee_name",
            "employee_email",
            "employee_designation",
            "employee_department",
            "reviewed_by_name",
            "status",
            "hr_comment",
            "submitted_at",
            "reviewed_at",
        ]
        read_only_fields = fields

    def get_employee_name(self, obj: ProfileReview) -> str:
        return obj.profile.full_name if obj.profile_id else ""

    def get_employee_email(self, obj: ProfileReview) -> str:
        return obj.profile.email if obj.profile_id else ""

    def get_employee_designation(self, obj: ProfileReview) -> str | None:
        return obj.profile.designation if obj.profile_id else None

    def get_employee_department(self, obj: ProfileReview) -> str | None:
        return obj.profile.department if obj.profile_id else None

    def get_reviewed_by_name(self, obj: ProfileReview) -> str | None:
        return obj.reviewed_by.full_name if obj.reviewed_by_id else None


class RejectInputSerializer(serializers.Serializer):
    """Input serializer for the reject endpoint."""

    comment = serializers.CharField(min_length=1)
