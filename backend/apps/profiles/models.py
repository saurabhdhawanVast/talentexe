from __future__ import annotations

# apps/profiles/models.py

import uuid

from django.contrib.postgres.fields import ArrayField
from django.db import models


class EmployeeProfile(models.Model):
    """
    Extended profile metadata for an employee.

    Maps 1-to-1 with UserProfile. Skills, certifications, projects, and
    education have been normalised into their own relational tables.

    managed=False — Supabase owns the DDL for `employee_profiles`.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    profile = models.OneToOneField(
        "users.UserProfile",
        on_delete=models.CASCADE,
        related_name="employee_profile",
        db_column="profile_id",
    )
    # [{name, proficiency}]
    languages = models.JSONField(default=list)
    summary = models.TextField(null=True, blank=True)
    linkedin_url = models.URLField(null=True, blank=True)
    github_url = models.URLField(null=True, blank=True)
    portfolio_url = models.URLField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "employee_profiles"
        managed = False

    def __str__(self) -> str:
        return f"EmployeeProfile({self.profile_id})"


class ResumeUpload(models.Model):
    """
    Tracks resume files uploaded to Supabase Storage.

    Only one row per profile should have is_current=True at any time;
    previous versions are kept for audit purposes.

    managed=False — Supabase owns the DDL for `resume_uploads`.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    profile = models.ForeignKey(
        "users.UserProfile",
        on_delete=models.CASCADE,
        related_name="resume_uploads",
        db_column="profile_id",
    )
    storage_path = models.TextField()
    original_name = models.CharField(max_length=255)
    mime_type = models.CharField(max_length=100)
    size_bytes = models.BigIntegerField()
    uploaded_at = models.DateTimeField(auto_now_add=True)
    is_current = models.BooleanField(default=True)
    extraction_status = models.CharField(max_length=20, default="pending")

    class Meta:
        db_table = "resume_uploads"
        managed = False

    def __str__(self) -> str:
        return f"ResumeUpload({self.original_name}, profile={self.profile_id})"


# ---------------------------------------------------------------------------
# Normalised skill tables
# ---------------------------------------------------------------------------


class SkillMaster(models.Model):
    """
    Master catalogue of skills. Shared across all employees.

    managed=False — Supabase owns the DDL for `skills_master`.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    name = models.CharField(max_length=255, unique=True)
    category = models.CharField(max_length=100, null=True, blank=True)
    aliases = ArrayField(models.TextField(), default=list, blank=True)  # text[]
    description = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "skills_master"
        managed = False

    def __str__(self) -> str:
        return self.name


class EmployeeSkill(models.Model):
    """
    Junction between a UserProfile and a SkillMaster entry.

    Carries proficiency metadata set by the employee or inferred by AI.

    managed=False — Supabase owns the DDL for `employee_skills`.
    """

    PROFICIENCY_CHOICES = [
        ("Beginner", "Beginner"),
        ("Intermediate", "Intermediate"),
        ("Expert", "Expert"),
    ]
    SOURCE_CHOICES = [
        ("manual", "manual"),
        ("ai_extracted", "ai_extracted"),
        ("inferred", "inferred"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    profile = models.ForeignKey(
        "users.UserProfile",
        on_delete=models.CASCADE,
        related_name="employee_skills",
        db_column="profile_id",
    )
    skill = models.ForeignKey(
        SkillMaster,
        on_delete=models.CASCADE,
        related_name="employee_skills",
    )
    proficiency_level = models.CharField(
        max_length=20, choices=PROFICIENCY_CHOICES, default="Intermediate"
    )
    years_of_experience = models.DecimalField(
        max_digits=4, decimal_places=1, null=True, blank=True
    )
    last_used_at = models.DateField(null=True, blank=True)
    is_primary = models.BooleanField(default=False)
    source = models.CharField(max_length=30, choices=SOURCE_CHOICES, default="manual")
    confidence_score = models.DecimalField(
        max_digits=3, decimal_places=2, null=True, blank=True
    )
    verified_by_hr = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "employee_skills"
        managed = False
        unique_together = [("profile", "skill")]

    def __str__(self) -> str:
        return f"{self.profile_id} — {self.skill_id}"


# ---------------------------------------------------------------------------
# Experience
# ---------------------------------------------------------------------------


class EmployeeExperience(models.Model):
    """
    Work experience entries for a UserProfile.

    managed=False — Supabase owns the DDL for `employee_experiences`.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    profile = models.ForeignKey(
        "users.UserProfile",
        on_delete=models.CASCADE,
        related_name="experiences",
        db_column="profile_id",
    )
    company_name = models.CharField(max_length=255)
    designation = models.CharField(max_length=255)
    employment_type = models.CharField(max_length=50, null=True, blank=True)
    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)
    is_current = models.BooleanField(default=False)
    location = models.CharField(max_length=255, null=True, blank=True)
    description = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "employee_experiences"
        managed = False

    def __str__(self) -> str:
        return f"{self.company_name} — {self.profile_id}"


# ---------------------------------------------------------------------------
# Projects
# ---------------------------------------------------------------------------


class Project(models.Model):
    """
    Project entries for a UserProfile.

    managed=False — Supabase owns the DDL for `projects`.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    profile = models.ForeignKey(
        "users.UserProfile",
        on_delete=models.CASCADE,
        related_name="projects",
        db_column="profile_id",
    )
    name = models.CharField(max_length=255)
    client_name = models.CharField(max_length=255, null=True, blank=True)
    description = models.TextField(null=True, blank=True)
    role = models.CharField(max_length=255, null=True, blank=True)
    team_size = models.IntegerField(null=True, blank=True)
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    is_current = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "projects"
        managed = False

    def __str__(self) -> str:
        return f"{self.name} — {self.profile_id}"


class ProjectSkill(models.Model):
    """
    Junction between a Project and a SkillMaster entry.

    managed=False — Supabase owns the DDL for `project_skills`.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        related_name="project_skills",
    )
    skill = models.ForeignKey(SkillMaster, on_delete=models.CASCADE)

    class Meta:
        db_table = "project_skills"
        managed = False
        unique_together = [("project", "skill")]

    def __str__(self) -> str:
        return f"{self.project_id} — {self.skill_id}"


# ---------------------------------------------------------------------------
# Certifications
# ---------------------------------------------------------------------------


class Certification(models.Model):
    """
    Professional certifications held by an employee.

    managed=False — Supabase owns the DDL for `certifications`.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    profile = models.ForeignKey(
        "users.UserProfile",
        on_delete=models.CASCADE,
        related_name="certifications",
        db_column="profile_id",
    )
    name = models.CharField(max_length=255)
    issuer = models.CharField(max_length=255, null=True, blank=True)
    issue_date = models.DateField(null=True, blank=True)
    expiry_date = models.DateField(null=True, blank=True)
    credential_url = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "certifications"
        managed = False

    def __str__(self) -> str:
        return f"{self.name} — {self.profile_id}"


# ---------------------------------------------------------------------------
# Education
# ---------------------------------------------------------------------------


class Education(models.Model):
    """
    Academic education entries for an employee.

    managed=False — Supabase owns the DDL for `education`.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    profile = models.ForeignKey(
        "users.UserProfile",
        on_delete=models.CASCADE,
        related_name="education_entries",
        db_column="profile_id",
    )
    degree = models.CharField(max_length=255)
    institution = models.CharField(max_length=255)
    start_year = models.IntegerField(null=True, blank=True)
    end_year = models.IntegerField(null=True, blank=True)
    grade = models.CharField(max_length=50, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "education"
        managed = False

    def __str__(self) -> str:
        return f"{self.degree} — {self.profile_id}"


# ---------------------------------------------------------------------------
# AI / embedding placeholder tables — no business logic in Phase 2.1
# ---------------------------------------------------------------------------


class AIProfileExtraction(models.Model):
    """
    Tracks AI-driven resume extraction jobs.

    managed=False — Supabase owns the DDL for `ai_profile_extractions`.
    """

    STATUS_CHOICES = [
        ("pending", "pending"),
        ("processing", "processing"),
        ("completed", "completed"),
        ("failed", "failed"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    profile = models.ForeignKey(
        "users.UserProfile",
        on_delete=models.CASCADE,
        related_name="ai_extractions",
        db_column="profile_id",
    )
    resume_upload = models.ForeignKey(
        ResumeUpload,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
    )
    raw_text = models.TextField(null=True, blank=True)
    extracted_json = models.JSONField(null=True, blank=True)
    model_name = models.CharField(max_length=100, null=True, blank=True)
    extraction_confidence = models.DecimalField(
        max_digits=3, decimal_places=2, null=True, blank=True
    )
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default="pending"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "ai_profile_extractions"
        managed = False

    def __str__(self) -> str:
        return f"AIProfileExtraction({self.profile_id}, {self.status})"


class InferredSkill(models.Model):
    """
    AI-inferred skill relationships (source skill implies inferred skill).

    managed=False — Supabase owns the DDL for `inferred_skills`.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    profile = models.ForeignKey(
        "users.UserProfile",
        on_delete=models.CASCADE,
        related_name="inferred_skills",
        db_column="profile_id",
    )
    source_skill = models.ForeignKey(
        SkillMaster,
        on_delete=models.CASCADE,
        related_name="source_inferences",
    )
    inferred_skill = models.ForeignKey(
        SkillMaster,
        on_delete=models.CASCADE,
        related_name="inferred_from",
    )
    confidence_score = models.DecimalField(max_digits=3, decimal_places=2)
    inference_reason = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "inferred_skills"
        managed = False

    def __str__(self) -> str:
        return f"InferredSkill({self.profile_id})"


class EmployeeEmbedding(models.Model):
    """
    Vector embedding snapshots for an employee profile (pgvector).

    The actual vector column is not represented here because Django's ORM
    does not natively support pgvector; queries against the vector column
    use raw SQL via the supabase-py client or psycopg2.

    managed=False — Supabase owns the DDL for `employee_embeddings`.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    profile = models.ForeignKey(
        "users.UserProfile",
        on_delete=models.CASCADE,
        related_name="embeddings",
        db_column="profile_id",
    )
    embedding_type = models.CharField(max_length=50, default="profile")
    searchable_text = models.TextField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "employee_embeddings"
        managed = False
        unique_together = [("profile", "embedding_type")]

    def __str__(self) -> str:
        return f"EmployeeEmbedding({self.profile_id}, {self.embedding_type})"
