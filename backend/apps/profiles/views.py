from __future__ import annotations

# apps/profiles/views.py

import logging
import uuid as uuid_module

from django.conf import settings
from django.db import IntegrityError
from django.http import HttpResponse
from django.utils import timezone
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.users.authentication import SupabaseJWTAuthentication
from apps.users.models import UserProfile
from apps.users.permissions import IsHR, IsHROrSelf
from apps.users.services import get_supabase_admin_client

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
from .pdf import generate_profile_pdf
from .serializers import (
    CertificationSerializer,
    EducationSerializer,
    EmployeeProfileSerializer,
    EmployeeProfileUpdateSerializer,
    EmployeeSkillCreateSerializer,
    EmployeeSkillSerializer,
    EmployeeSkillUpdateSerializer,
    ExperienceSerializer,
    ProjectSerializer,
    ResumeUploadSerializer,
    SkillMasterSerializer,
    UserProfileUpdateSerializer,
)

logger = logging.getLogger(__name__)

_AUTH = [SupabaseJWTAuthentication]

ALLOWED_RESUME_TYPES = {
    "application/pdf",
    "application/msword",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
}
ALLOWED_RESUME_EXTENSIONS = {".pdf", ".doc", ".docx"}
MAX_RESUME_SIZE = 10 * 1024 * 1024  # 10 MB


# ---------------------------------------------------------------------------
# Response helpers
# ---------------------------------------------------------------------------


def _ok(data: object, meta: dict | None = None, http_status: int = 200) -> Response:
    return Response(
        {"data": data, "error": None, "meta": meta or {}}, status=http_status
    )


def _err(message: str, detail: str = "", http_status: int = 400) -> Response:
    return Response(
        {"data": None, "error": message, "meta": {"detail": detail}},
        status=http_status,
    )


def _get_profile_or_404(pk: str) -> tuple[UserProfile | None, Response | None]:
    try:
        return UserProfile.objects.get(id=pk), None
    except UserProfile.DoesNotExist:
        return None, _err("User not found.", http_status=404)


# ---------------------------------------------------------------------------
# Shared access-control helper
# ---------------------------------------------------------------------------


def _can_access(request: Request, profile: UserProfile) -> bool:
    """HR can access any profile; employees only their own."""
    if request.user.role == "hr":
        return True
    return str(request.user.id) == str(profile.id)


# ---------------------------------------------------------------------------
# Existing views (updated)
# ---------------------------------------------------------------------------


class ProfileDetailView(APIView):
    """
    GET   /api/v1/profiles/{id}/  — Return combined UserProfile + EmployeeProfile.
    PATCH /api/v1/profiles/{id}/  — Update both layers. HR can update anyone;
                                    employee can only update their own profile.

    The ``employee`` payload now only carries summary/languages/URLs.
    Skills, certifications, projects, and education are managed through
    their own dedicated sub-resource endpoints.
    """

    authentication_classes = _AUTH
    permission_classes = [IsAuthenticated]

    def _can_access(self, request: Request, profile: UserProfile) -> bool:
        """HR can access any profile; employees only their own."""
        if request.user.role == "hr":
            return True
        return str(request.user.id) == str(profile.id)

    def get(self, request: Request, pk: str) -> Response:
        profile, err = _get_profile_or_404(str(pk))
        if err:
            return err

        if not self._can_access(request, profile):
            return _err("Permission denied.", http_status=403)

        try:
            employee = profile.employee_profile
        except EmployeeProfile.DoesNotExist:
            employee = None

        full_user_data = {
            "id": str(profile.id),
            "email": profile.email,
            "full_name": profile.full_name,
            "role": profile.role,
            "is_active": profile.is_active,
            "phone": profile.phone,
            "designation": profile.designation,
            "department": profile.department,
            "experience_years": (
                str(profile.experience_years) if profile.experience_years else None
            ),
            "location": profile.location,
            "avatar_url": profile.avatar_url,
            "must_change_password": profile.must_change_password,
            "profile_status": profile.profile_status,
            "created_at": profile.created_at,
            "updated_at": profile.updated_at,
        }
        return _ok(
            {
                "user": full_user_data,
                "employee": EmployeeProfileSerializer(employee).data if employee else None,
            }
        )

    def patch(self, request: Request, pk: str) -> Response:
        profile, err = _get_profile_or_404(str(pk))
        if err:
            return err

        if not self._can_access(request, profile):
            return _err("Permission denied.", http_status=403)

        user_data: dict = request.data.get("user", {})
        employee_data: dict = request.data.get("employee", {})

        if user_data:
            user_serializer = UserProfileUpdateSerializer(
                profile, data=user_data, partial=True
            )
            if not user_serializer.is_valid():
                return _err(
                    "Validation error in user fields.",
                    detail=str(user_serializer.errors),
                )
            user_serializer.save()

        if employee_data:
            try:
                employee = profile.employee_profile
            except EmployeeProfile.DoesNotExist:
                employee = EmployeeProfile(profile=profile)

            emp_serializer = EmployeeProfileUpdateSerializer(
                employee, data=employee_data, partial=True
            )
            if not emp_serializer.is_valid():
                return _err(
                    "Validation error in employee fields.",
                    detail=str(emp_serializer.errors),
                )
            emp_serializer.save()

        return _ok({"message": "Profile updated successfully."})


class ResumeUploadView(APIView):
    """
    POST /api/v1/profiles/{id}/resume/
        Upload a resume file. Validates type and size, uploads to Supabase Storage,
        marks previous resumes is_current=False, inserts a new ResumeUpload row.

    GET  /api/v1/profiles/{id}/resume/
        Return a signed URL (1 hour) for the current resume.
    """

    authentication_classes = _AUTH
    permission_classes = [IsAuthenticated]

    def _can_access(self, request: Request, profile: UserProfile) -> bool:
        if request.user.role == "hr":
            return True
        return str(request.user.id) == str(profile.id)

    def post(self, request: Request, pk: str) -> Response:
        profile, err = _get_profile_or_404(str(pk))
        if err:
            return err

        if not self._can_access(request, profile):
            return _err("Permission denied.", http_status=403)

        if "file" not in request.FILES:
            return _err("No file uploaded. Include a 'file' key in the request.")

        uploaded = request.FILES["file"]
        file_name: str = uploaded.name or "resume"
        mime_type: str = uploaded.content_type or "application/octet-stream"
        file_bytes: bytes = uploaded.read()
        size_bytes: int = len(file_bytes)

        if size_bytes > MAX_RESUME_SIZE:
            return _err("Resume must be smaller than 10 MB.")

        ext = "." + file_name.rsplit(".", 1)[-1].lower() if "." in file_name else ""
        if ext not in ALLOWED_RESUME_EXTENSIONS and mime_type not in ALLOWED_RESUME_TYPES:
            return _err(
                "Only PDF, DOC, and DOCX files are accepted.",
                detail=f"Received: {mime_type}",
            )

        safe_name = file_name.replace(" ", "_")
        storage_path = f"{pk}/{uuid_module.uuid4()}_{safe_name}"
        bucket = settings.SUPABASE_STORAGE_BUCKET_RESUMES

        try:
            client = get_supabase_admin_client()
            client.storage.from_(bucket).upload(
                storage_path,
                file_bytes,
                {"content-type": mime_type},
            )
        except Exception as exc:
            logger.error("Supabase Storage upload failed for profile %s: %s", pk, exc)
            return _err("Failed to upload file to storage.", detail=str(exc), http_status=500)

        ResumeUpload.objects.filter(profile=profile, is_current=True).update(
            is_current=False
        )

        resume = ResumeUpload.objects.create(
            profile=profile,
            storage_path=storage_path,
            original_name=file_name,
            mime_type=mime_type,
            size_bytes=size_bytes,
            is_current=True,
        )

        return _ok(ResumeUploadSerializer(resume).data, http_status=201)

    def get(self, request: Request, pk: str) -> Response:
        profile, err = _get_profile_or_404(str(pk))
        if err:
            return err

        if not self._can_access(request, profile):
            return _err("Permission denied.", http_status=403)

        try:
            resume = ResumeUpload.objects.get(profile=profile, is_current=True)
        except ResumeUpload.DoesNotExist:
            return _err("No resume found for this profile.", http_status=404)

        bucket = settings.SUPABASE_STORAGE_BUCKET_RESUMES
        try:
            client = get_supabase_admin_client()
            result = client.storage.from_(bucket).create_signed_url(
                resume.storage_path, 3600
            )
            signed_url: str = result.get("signedURL") or result.get("signed_url", "")
        except Exception as exc:
            logger.error("Signed URL generation failed for %s: %s", pk, exc)
            return _err("Failed to generate download URL.", detail=str(exc), http_status=500)

        return _ok(
            {
                "url": signed_url,
                "original_name": resume.original_name,
                "expires_in_seconds": 3600,
            }
        )

    def delete(self, request: Request, pk: str) -> Response:
        profile, err = _get_profile_or_404(str(pk))
        if err:
            return err

        if not self._can_access(request, profile):
            return _err("Permission denied.", http_status=403)

        try:
            resume = ResumeUpload.objects.get(profile=profile, is_current=True)
        except ResumeUpload.DoesNotExist:
            return _err("No resume found for this profile.", http_status=404)

        bucket = settings.SUPABASE_STORAGE_BUCKET_RESUMES
        try:
            client = get_supabase_admin_client()
            client.storage.from_(bucket).remove([resume.storage_path])
        except Exception as exc:
            logger.warning("Failed to delete file from Supabase Storage for %s: %s", pk, exc)

        resume.delete()
        return _ok({"message": "Resume removed successfully."})


class SubmitReviewView(APIView):
    """
    POST /api/v1/profiles/{id}/submit-review/

    Employee submits their profile for HR review.
    Sets profile_status='submitted' and creates a pending ProfileReview row.
    """

    authentication_classes = _AUTH
    permission_classes = [IsAuthenticated]

    def post(self, request: Request, pk: str) -> Response:
        profile, err = _get_profile_or_404(str(pk))
        if err:
            return err

        if str(request.user.id) != str(profile.id):
            return _err(
                "You can only submit your own profile for review.", http_status=403
            )

        if profile.profile_status == "approved":
            return _err("This profile has already been approved.")

        if profile.profile_status == "submitted":
            return _err("This profile is already under review.")

        from apps.reviews.models import ProfileReview  # noqa: PLC0415

        profile.profile_status = "submitted"
        profile.save(update_fields=["profile_status"])

        ProfileReview.objects.create(
            profile=profile,
            status="pending",
        )

        return _ok({"message": "Profile submitted for review.", "profile_status": "submitted"})


class DownloadProfileView(APIView):
    """
    GET /api/v1/profiles/{id}/download/

    HR only. Queries all normalised tables, then generates a PDF and returns it
    as a file download.
    """

    authentication_classes = _AUTH
    permission_classes = [IsAuthenticated, IsHR]

    def get(self, request: Request, pk: str) -> HttpResponse | Response:
        profile, err = _get_profile_or_404(str(pk))
        if err:
            return err

        try:
            employee = profile.employee_profile
        except EmployeeProfile.DoesNotExist:
            employee = None

        # Query all normalised tables for this profile
        skills = list(
            EmployeeSkill.objects.filter(profile=profile).select_related("skill")
        )
        experiences = list(EmployeeExperience.objects.filter(profile=profile))
        projects = list(
            Project.objects.filter(profile=profile).prefetch_related(
                "project_skills__skill"
            )
        )
        certifications = list(Certification.objects.filter(profile=profile))
        education = list(Education.objects.filter(profile=profile))

        try:
            pdf_bytes = generate_profile_pdf(
                user=profile,
                employee=employee,
                skills=skills,
                experiences=experiences,
                projects=projects,
                certifications=certifications,
                education=education,
            )
        except Exception as exc:
            logger.error("PDF generation failed for profile %s: %s", pk, exc)
            return _err("PDF generation failed.", detail=str(exc), http_status=500)

        safe_name = profile.full_name.replace(" ", "_").replace("/", "_")
        response = HttpResponse(pdf_bytes, content_type="application/pdf")
        response["Content-Disposition"] = (
            f'attachment; filename="{safe_name}_profile.pdf"'
        )
        return response


# ---------------------------------------------------------------------------
# Skills master
# ---------------------------------------------------------------------------


class SkillsMasterView(APIView):
    """
    GET  /api/v1/skills/  — List all skills in the master catalogue.
    POST /api/v1/skills/  — Get-or-create a skill by name (case-insensitive).
    """

    authentication_classes = _AUTH
    permission_classes = [IsAuthenticated]

    def get(self, request: Request) -> Response:
        skills = SkillMaster.objects.all().order_by("name")
        return _ok(SkillMasterSerializer(skills, many=True).data)

    def post(self, request: Request) -> Response:
        name: str = request.data.get("name", "").strip()
        if not name:
            return _err("'name' is required.")

        skill, created = SkillMaster.objects.get_or_create(
            name__iexact=name,
            defaults={"name": name, "category": request.data.get("category")},
        )
        return _ok(
            SkillMasterSerializer(skill).data,
            http_status=201 if created else 200,
        )


# ---------------------------------------------------------------------------
# Profile skills
# ---------------------------------------------------------------------------


class ProfileSkillsView(APIView):
    """
    GET  /api/v1/profiles/{pk}/skills/  — List all skills for a profile.
    POST /api/v1/profiles/{pk}/skills/  — Add a skill to a profile.
    """

    authentication_classes = _AUTH
    permission_classes = [IsAuthenticated]

    def get(self, request: Request, pk: str) -> Response:
        profile, err = _get_profile_or_404(str(pk))
        if err:
            return err
        if not _can_access(request, profile):
            return _err("Permission denied.", http_status=403)

        employee_skills = (
            EmployeeSkill.objects.filter(profile=profile)
            .select_related("skill")
            .order_by("skill__name")
        )
        return _ok(EmployeeSkillSerializer(employee_skills, many=True).data)

    def post(self, request: Request, pk: str) -> Response:
        profile, err = _get_profile_or_404(str(pk))
        if err:
            return err
        if not _can_access(request, profile):
            return _err("Permission denied.", http_status=403)

        serializer = EmployeeSkillCreateSerializer(data=request.data)
        if not serializer.is_valid():
            return _err("Validation error.", detail=str(serializer.errors))

        vd = serializer.validated_data
        skill_name: str = vd["skill_name"].strip()

        # Case-insensitive get-or-create on SkillMaster
        skill, _ = SkillMaster.objects.get_or_create(
            name__iexact=skill_name,
            defaults={"name": skill_name},
        )

        # Detect duplicate before attempting insert
        if EmployeeSkill.objects.filter(profile=profile, skill=skill).exists():
            return _err(
                "Skill already added to this profile.",
                detail=f"skill_name={skill_name}",
                http_status=409,
            )

        try:
            employee_skill = EmployeeSkill.objects.create(
                profile=profile,
                skill=skill,
                proficiency_level=vd["proficiency_level"],
                years_of_experience=vd.get("years_of_experience"),
                is_primary=vd["is_primary"],
                source="manual",
            )
        except IntegrityError:
            return _err(
                "Skill already added to this profile.",
                http_status=409,
            )

        return _ok(
            EmployeeSkillSerializer(employee_skill).data,
            http_status=201,
        )


class ProfileSkillDetailView(APIView):
    """
    PATCH  /api/v1/profiles/{pk}/skills/{sk}/  — Update proficiency/years/is_primary.
    DELETE /api/v1/profiles/{pk}/skills/{sk}/  — Remove the skill link.
    """

    authentication_classes = _AUTH
    permission_classes = [IsAuthenticated]

    def _get_skill_or_404(
        self, profile: UserProfile, sk: str
    ) -> tuple[EmployeeSkill | None, Response | None]:
        try:
            return (
                EmployeeSkill.objects.select_related("skill").get(
                    id=sk, profile=profile
                ),
                None,
            )
        except EmployeeSkill.DoesNotExist:
            return None, _err("Skill not found for this profile.", http_status=404)

    def patch(self, request: Request, pk: str, sk: str) -> Response:
        profile, err = _get_profile_or_404(str(pk))
        if err:
            return err
        if not _can_access(request, profile):
            return _err("Permission denied.", http_status=403)

        employee_skill, err = self._get_skill_or_404(profile, str(sk))
        if err:
            return err

        serializer = EmployeeSkillUpdateSerializer(
            employee_skill, data=request.data, partial=True
        )
        if not serializer.is_valid():
            return _err("Validation error.", detail=str(serializer.errors))

        serializer.save()
        return _ok(EmployeeSkillSerializer(employee_skill).data)

    def delete(self, request: Request, pk: str, sk: str) -> Response:
        profile, err = _get_profile_or_404(str(pk))
        if err:
            return err
        if not _can_access(request, profile):
            return _err("Permission denied.", http_status=403)

        employee_skill, err = self._get_skill_or_404(profile, str(sk))
        if err:
            return err

        employee_skill.delete()
        return _ok({"message": "Skill removed."})


# ---------------------------------------------------------------------------
# Profile experiences
# ---------------------------------------------------------------------------


class ProfileExperiencesView(APIView):
    """
    GET  /api/v1/profiles/{pk}/experiences/  — List work experience entries.
    POST /api/v1/profiles/{pk}/experiences/  — Add a new experience entry.
    """

    authentication_classes = _AUTH
    permission_classes = [IsAuthenticated]

    def get(self, request: Request, pk: str) -> Response:
        profile, err = _get_profile_or_404(str(pk))
        if err:
            return err
        if not _can_access(request, profile):
            return _err("Permission denied.", http_status=403)

        experiences = EmployeeExperience.objects.filter(profile=profile).order_by(
            "-start_date"
        )
        return _ok(ExperienceSerializer(experiences, many=True).data)

    def post(self, request: Request, pk: str) -> Response:
        profile, err = _get_profile_or_404(str(pk))
        if err:
            return err
        if not _can_access(request, profile):
            return _err("Permission denied.", http_status=403)

        serializer = ExperienceSerializer(data=request.data)
        if not serializer.is_valid():
            return _err("Validation error.", detail=str(serializer.errors))

        experience = serializer.save(profile=profile)
        return _ok(ExperienceSerializer(experience).data, http_status=201)


class ProfileExperienceDetailView(APIView):
    """
    PATCH  /api/v1/profiles/{pk}/experiences/{ek}/
    DELETE /api/v1/profiles/{pk}/experiences/{ek}/
    """

    authentication_classes = _AUTH
    permission_classes = [IsAuthenticated]

    def _get_experience_or_404(
        self, profile: UserProfile, ek: str
    ) -> tuple[EmployeeExperience | None, Response | None]:
        try:
            return EmployeeExperience.objects.get(id=ek, profile=profile), None
        except EmployeeExperience.DoesNotExist:
            return None, _err("Experience entry not found.", http_status=404)

    def patch(self, request: Request, pk: str, ek: str) -> Response:
        profile, err = _get_profile_or_404(str(pk))
        if err:
            return err
        if not _can_access(request, profile):
            return _err("Permission denied.", http_status=403)

        experience, err = self._get_experience_or_404(profile, str(ek))
        if err:
            return err

        serializer = ExperienceSerializer(experience, data=request.data, partial=True)
        if not serializer.is_valid():
            return _err("Validation error.", detail=str(serializer.errors))

        serializer.save()
        return _ok(ExperienceSerializer(experience).data)

    def delete(self, request: Request, pk: str, ek: str) -> Response:
        profile, err = _get_profile_or_404(str(pk))
        if err:
            return err
        if not _can_access(request, profile):
            return _err("Permission denied.", http_status=403)

        experience, err = self._get_experience_or_404(profile, str(ek))
        if err:
            return err

        experience.delete()
        return _ok({"message": "Experience entry deleted."})


# ---------------------------------------------------------------------------
# Profile projects
# ---------------------------------------------------------------------------


def _sync_project_skills(project: Project, skill_names: list[str]) -> None:
    """
    Delete existing ProjectSkill rows for ``project`` and re-create them
    from ``skill_names``, performing get-or-create on SkillMaster.
    """
    ProjectSkill.objects.filter(project=project).delete()
    for raw_name in skill_names:
        name = raw_name.strip()
        if not name:
            continue
        skill, _ = SkillMaster.objects.get_or_create(
            name__iexact=name,
            defaults={"name": name},
        )
        ProjectSkill.objects.get_or_create(project=project, skill=skill)


class ProfileProjectsView(APIView):
    """
    GET  /api/v1/profiles/{pk}/projects/  — List projects (with skills).
    POST /api/v1/profiles/{pk}/projects/  — Create a project; optionally link skills.
    """

    authentication_classes = _AUTH
    permission_classes = [IsAuthenticated]

    def get(self, request: Request, pk: str) -> Response:
        profile, err = _get_profile_or_404(str(pk))
        if err:
            return err
        if not _can_access(request, profile):
            return _err("Permission denied.", http_status=403)

        projects = (
            Project.objects.filter(profile=profile)
            .prefetch_related("project_skills__skill")
            .order_by("-start_date")
        )
        return _ok(ProjectSerializer(projects, many=True).data)

    def post(self, request: Request, pk: str) -> Response:
        profile, err = _get_profile_or_404(str(pk))
        if err:
            return err
        if not _can_access(request, profile):
            return _err("Permission denied.", http_status=403)

        serializer = ProjectSerializer(data=request.data)
        if not serializer.is_valid():
            return _err("Validation error.", detail=str(serializer.errors))

        skill_names: list[str] = serializer.validated_data.pop("skill_names", [])
        project = serializer.save(profile=profile)

        if skill_names:
            _sync_project_skills(project, skill_names)

        # Re-fetch with prefetch so the response includes skills
        project.refresh_from_db()
        project_with_skills = (
            Project.objects.prefetch_related("project_skills__skill").get(pk=project.pk)
        )
        return _ok(ProjectSerializer(project_with_skills).data, http_status=201)


class ProfileProjectDetailView(APIView):
    """
    PATCH  /api/v1/profiles/{pk}/projects/{proj_pk}/
    DELETE /api/v1/profiles/{pk}/projects/{proj_pk}/
    """

    authentication_classes = _AUTH
    permission_classes = [IsAuthenticated]

    def _get_project_or_404(
        self, profile: UserProfile, proj_pk: str
    ) -> tuple[Project | None, Response | None]:
        try:
            return (
                Project.objects.prefetch_related("project_skills__skill").get(
                    id=proj_pk, profile=profile
                ),
                None,
            )
        except Project.DoesNotExist:
            return None, _err("Project not found.", http_status=404)

    def patch(self, request: Request, pk: str, proj_pk: str) -> Response:
        profile, err = _get_profile_or_404(str(pk))
        if err:
            return err
        if not _can_access(request, profile):
            return _err("Permission denied.", http_status=403)

        project, err = self._get_project_or_404(profile, str(proj_pk))
        if err:
            return err

        serializer = ProjectSerializer(project, data=request.data, partial=True)
        if not serializer.is_valid():
            return _err("Validation error.", detail=str(serializer.errors))

        skill_names: list[str] | None = serializer.validated_data.pop(
            "skill_names", None
        )
        serializer.save()

        if skill_names is not None:
            _sync_project_skills(project, skill_names)

        # Re-fetch with prefetch for accurate response
        project_with_skills = (
            Project.objects.prefetch_related("project_skills__skill").get(pk=project.pk)
        )
        return _ok(ProjectSerializer(project_with_skills).data)

    def delete(self, request: Request, pk: str, proj_pk: str) -> Response:
        profile, err = _get_profile_or_404(str(pk))
        if err:
            return err
        if not _can_access(request, profile):
            return _err("Permission denied.", http_status=403)

        project, err = self._get_project_or_404(profile, str(proj_pk))
        if err:
            return err

        project.delete()
        return _ok({"message": "Project deleted."})


# ---------------------------------------------------------------------------
# Profile certifications
# ---------------------------------------------------------------------------


class ProfileCertificationsView(APIView):
    """
    GET  /api/v1/profiles/{pk}/certifications/
    POST /api/v1/profiles/{pk}/certifications/
    """

    authentication_classes = _AUTH
    permission_classes = [IsAuthenticated]

    def get(self, request: Request, pk: str) -> Response:
        profile, err = _get_profile_or_404(str(pk))
        if err:
            return err
        if not _can_access(request, profile):
            return _err("Permission denied.", http_status=403)

        certs = Certification.objects.filter(profile=profile).order_by("-issue_date")
        return _ok(CertificationSerializer(certs, many=True).data)

    def post(self, request: Request, pk: str) -> Response:
        profile, err = _get_profile_or_404(str(pk))
        if err:
            return err
        if not _can_access(request, profile):
            return _err("Permission denied.", http_status=403)

        serializer = CertificationSerializer(data=request.data)
        if not serializer.is_valid():
            return _err("Validation error.", detail=str(serializer.errors))

        cert = serializer.save(profile=profile)
        return _ok(CertificationSerializer(cert).data, http_status=201)


class ProfileCertificationDetailView(APIView):
    """
    PATCH  /api/v1/profiles/{pk}/certifications/{ck}/
    DELETE /api/v1/profiles/{pk}/certifications/{ck}/
    """

    authentication_classes = _AUTH
    permission_classes = [IsAuthenticated]

    def _get_cert_or_404(
        self, profile: UserProfile, ck: str
    ) -> tuple[Certification | None, Response | None]:
        try:
            return Certification.objects.get(id=ck, profile=profile), None
        except Certification.DoesNotExist:
            return None, _err("Certification not found.", http_status=404)

    def patch(self, request: Request, pk: str, ck: str) -> Response:
        profile, err = _get_profile_or_404(str(pk))
        if err:
            return err
        if not _can_access(request, profile):
            return _err("Permission denied.", http_status=403)

        cert, err = self._get_cert_or_404(profile, str(ck))
        if err:
            return err

        serializer = CertificationSerializer(cert, data=request.data, partial=True)
        if not serializer.is_valid():
            return _err("Validation error.", detail=str(serializer.errors))

        serializer.save()
        return _ok(CertificationSerializer(cert).data)

    def delete(self, request: Request, pk: str, ck: str) -> Response:
        profile, err = _get_profile_or_404(str(pk))
        if err:
            return err
        if not _can_access(request, profile):
            return _err("Permission denied.", http_status=403)

        cert, err = self._get_cert_or_404(profile, str(ck))
        if err:
            return err

        cert.delete()
        return _ok({"message": "Certification deleted."})


# ---------------------------------------------------------------------------
# Profile education
# ---------------------------------------------------------------------------


class ProfileEducationView(APIView):
    """
    GET  /api/v1/profiles/{pk}/education/
    POST /api/v1/profiles/{pk}/education/
    """

    authentication_classes = _AUTH
    permission_classes = [IsAuthenticated]

    def get(self, request: Request, pk: str) -> Response:
        profile, err = _get_profile_or_404(str(pk))
        if err:
            return err
        if not _can_access(request, profile):
            return _err("Permission denied.", http_status=403)

        entries = Education.objects.filter(profile=profile).order_by("-end_year")
        return _ok(EducationSerializer(entries, many=True).data)

    def post(self, request: Request, pk: str) -> Response:
        profile, err = _get_profile_or_404(str(pk))
        if err:
            return err
        if not _can_access(request, profile):
            return _err("Permission denied.", http_status=403)

        serializer = EducationSerializer(data=request.data)
        if not serializer.is_valid():
            return _err("Validation error.", detail=str(serializer.errors))

        entry = serializer.save(profile=profile)
        return _ok(EducationSerializer(entry).data, http_status=201)


class ProfileEducationDetailView(APIView):
    """
    PATCH  /api/v1/profiles/{pk}/education/{ek}/
    DELETE /api/v1/profiles/{pk}/education/{ek}/
    """

    authentication_classes = _AUTH
    permission_classes = [IsAuthenticated]

    def _get_education_or_404(
        self, profile: UserProfile, ek: str
    ) -> tuple[Education | None, Response | None]:
        try:
            return Education.objects.get(id=ek, profile=profile), None
        except Education.DoesNotExist:
            return None, _err("Education entry not found.", http_status=404)

    def patch(self, request: Request, pk: str, ek: str) -> Response:
        profile, err = _get_profile_or_404(str(pk))
        if err:
            return err
        if not _can_access(request, profile):
            return _err("Permission denied.", http_status=403)

        entry, err = self._get_education_or_404(profile, str(ek))
        if err:
            return err

        serializer = EducationSerializer(entry, data=request.data, partial=True)
        if not serializer.is_valid():
            return _err("Validation error.", detail=str(serializer.errors))

        serializer.save()
        return _ok(EducationSerializer(entry).data)

    def delete(self, request: Request, pk: str, ek: str) -> Response:
        profile, err = _get_profile_or_404(str(pk))
        if err:
            return err
        if not _can_access(request, profile):
            return _err("Permission denied.", http_status=403)

        entry, err = self._get_education_or_404(profile, str(ek))
        if err:
            return err

        entry.delete()
        return _ok({"message": "Education entry deleted."})
