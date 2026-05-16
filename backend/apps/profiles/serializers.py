from __future__ import annotations

# apps/profiles/serializers.py

from rest_framework import serializers

from apps.users.models import UserProfile
from apps.users.serializers import UserProfileSerializer

from .models import (
    Certification,
    Education,
    EmployeeExperience,
    EmployeeProfile,
    EmployeeSkill,
    Project,
    ProjectSkill,
    ResumeUpload,
    SkillMaster,
)


# ---------------------------------------------------------------------------
# EmployeeProfile (core metadata — no longer carries JSONB skill/cert/etc.)
# ---------------------------------------------------------------------------


class EmployeeProfileSerializer(serializers.ModelSerializer):
    """Full serializer for EmployeeProfile — used in GET."""

    class Meta:
        model = EmployeeProfile
        fields = [
            "id",
            "languages",
            "summary",
            "linkedin_url",
            "github_url",
            "portfolio_url",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class EmployeeProfileUpdateSerializer(serializers.ModelSerializer):
    """
    Input serializer for PATCH on EmployeeProfile fields.

    All fields are optional so partial updates work correctly.
    Skills, certifications, projects, and education are now managed
    through their own dedicated endpoints.
    """

    class Meta:
        model = EmployeeProfile
        fields = [
            "languages",
            "summary",
            "linkedin_url",
            "github_url",
            "portfolio_url",
        ]


class ProfileDetailSerializer(serializers.Serializer):
    """
    Combined read serializer that merges UserProfile + EmployeeProfile into
    a single flat response. Used by ProfileDetailView GET.
    """

    user = UserProfileSerializer()
    employee = EmployeeProfileSerializer(allow_null=True)


class UserProfileUpdateSerializer(serializers.ModelSerializer):
    """
    Input serializer for PATCH on the UserProfile portion of a profile.
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


# ---------------------------------------------------------------------------
# ResumeUpload
# ---------------------------------------------------------------------------


class ResumeUploadSerializer(serializers.ModelSerializer):
    """Read serializer for a ResumeUpload row."""

    class Meta:
        model = ResumeUpload
        fields = [
            "id",
            "original_name",
            "mime_type",
            "size_bytes",
            "uploaded_at",
            "is_current",
            "extraction_status",
        ]
        read_only_fields = fields


# ---------------------------------------------------------------------------
# Skills
# ---------------------------------------------------------------------------


class SkillMasterSerializer(serializers.ModelSerializer):
    """Read serializer for a SkillMaster entry."""

    class Meta:
        model = SkillMaster
        fields = ["id", "name", "category", "aliases"]


class EmployeeSkillSerializer(serializers.ModelSerializer):
    """Read serializer for an EmployeeSkill — includes denormalised skill name/category."""

    name = serializers.CharField(source="skill.name", read_only=True)
    category = serializers.CharField(source="skill.category", read_only=True)

    class Meta:
        model = EmployeeSkill
        fields = [
            "id",
            "skill_id",
            "name",
            "category",
            "proficiency_level",
            "years_of_experience",
            "is_primary",
            "source",
            "verified_by_hr",
            "created_at",
        ]
        read_only_fields = ["id", "source", "verified_by_hr", "created_at"]


class EmployeeSkillCreateSerializer(serializers.Serializer):
    """
    Input serializer for POST /profiles/{pk}/skills/.

    The skill is identified by name; the view performs get-or-create on
    SkillMaster (case-insensitive) before creating the EmployeeSkill row.
    """

    skill_name = serializers.CharField(max_length=255)
    proficiency_level = serializers.ChoiceField(
        choices=["Beginner", "Intermediate", "Expert"],
        default="Intermediate",
    )
    years_of_experience = serializers.DecimalField(
        max_digits=4,
        decimal_places=1,
        required=False,
        allow_null=True,
    )
    is_primary = serializers.BooleanField(default=False)


class EmployeeSkillUpdateSerializer(serializers.ModelSerializer):
    """Input serializer for PATCH /profiles/{pk}/skills/{sk}/."""

    class Meta:
        model = EmployeeSkill
        fields = ["proficiency_level", "years_of_experience", "is_primary"]


# ---------------------------------------------------------------------------
# Experience
# ---------------------------------------------------------------------------


class ExperienceSerializer(serializers.ModelSerializer):
    """Read/write serializer for EmployeeExperience."""

    class Meta:
        model = EmployeeExperience
        fields = [
            "id",
            "company_name",
            "designation",
            "employment_type",
            "start_date",
            "end_date",
            "is_current",
            "location",
            "description",
            "created_at",
        ]
        read_only_fields = ["id", "created_at"]


# ---------------------------------------------------------------------------
# Projects
# ---------------------------------------------------------------------------


class ProjectSkillSerializer(serializers.ModelSerializer):
    """Nested read serializer for skills attached to a project."""

    name = serializers.CharField(source="skill.name", read_only=True)
    skill_id = serializers.UUIDField(source="skill.id", read_only=True)

    class Meta:
        model = ProjectSkill
        fields = ["skill_id", "name"]


class ProjectSerializer(serializers.ModelSerializer):
    """
    Read/write serializer for Project.

    On write, ``skill_names`` (list of strings) is accepted; the view
    resolves/creates the corresponding SkillMaster rows and writes
    ProjectSkill rows. On read, ``skills`` returns the nested list.
    """

    skills = ProjectSkillSerializer(source="project_skills", many=True, read_only=True)
    skill_names = serializers.ListField(
        child=serializers.CharField(), write_only=True, required=False
    )

    class Meta:
        model = Project
        fields = [
            "id",
            "name",
            "client_name",
            "description",
            "role",
            "team_size",
            "start_date",
            "end_date",
            "is_current",
            "skills",
            "skill_names",
            "created_at",
        ]
        read_only_fields = ["id", "created_at"]


# ---------------------------------------------------------------------------
# Certifications
# ---------------------------------------------------------------------------


class CertificationSerializer(serializers.ModelSerializer):
    """Read/write serializer for Certification."""

    class Meta:
        model = Certification
        fields = [
            "id",
            "name",
            "issuer",
            "issue_date",
            "expiry_date",
            "credential_url",
            "created_at",
        ]
        read_only_fields = ["id", "created_at"]


# ---------------------------------------------------------------------------
# Education
# ---------------------------------------------------------------------------


class EducationSerializer(serializers.ModelSerializer):
    """Read/write serializer for Education."""

    class Meta:
        model = Education
        fields = [
            "id",
            "degree",
            "institution",
            "start_year",
            "end_year",
            "grade",
            "created_at",
        ]
        read_only_fields = ["id", "created_at"]
