from __future__ import annotations

# apps/ai_integration/pipeline.py

"""
Resume extraction pipeline.

Orchestrates the full flow:
  1. Load ResumeUpload from DB
  2. Create/update AIProfileExtraction row
  3. Download file bytes from Supabase Storage
  4. Extract plain text
  5. Call Ollama for structured data
  6. Write extracted data to normalised profile tables
  7. Update status fields on both rows

All DB writes use the Django ORM. Supabase Storage downloads use the
admin supabase-py client. `managed=False` models are used throughout —
no migrations are generated or run by this module.
"""

import json
import logging
import uuid
from datetime import date, datetime
from typing import Any

from django.conf import settings
from django.db import IntegrityError

from apps.profiles.models import (
    AIProfileExtraction,
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
from apps.users.models import UserProfile
from apps.users.services import get_supabase_admin_client

from . import extractor, text_extractor

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Date parsing helpers
# ---------------------------------------------------------------------------


def _parse_date(value: Any) -> date | None:
    """
    Parse a YYYY-MM-DD string into a ``datetime.date``.

    Returns None for null/empty values or any malformed string rather than
    raising so that a single bad date field does not abort the whole row.
    """
    if not value:
        return None
    if isinstance(value, date):
        return value
    try:
        return datetime.strptime(str(value), "%Y-%m-%d").date()
    except (ValueError, TypeError):
        logger.warning("Could not parse date value: %r — skipping field.", value)
        return None


def _parse_int(value: Any) -> int | None:
    """Coerce to int or return None."""
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _parse_float(value: Any) -> float | None:
    """Coerce to float or return None."""
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


# ---------------------------------------------------------------------------
# Skill helpers
# ---------------------------------------------------------------------------

_PROFICIENCY_MAP: dict[str, str] = {
    "beginner": "Beginner",
    "intermediate": "Intermediate",
    "expert": "Expert",
    "advanced": "Expert",
    "proficient": "Intermediate",
}


def _normalize_proficiency(raw: Any) -> str:
    """Map LLM proficiency strings to EmployeeSkill.PROFICIENCY_CHOICES."""
    normalized = _PROFICIENCY_MAP.get(str(raw).lower().strip(), "Intermediate")
    return normalized


def _get_or_create_skill(name: str) -> SkillMaster | None:
    """
    Case-insensitive get-or-create for SkillMaster.

    Returns None if name is empty/None so callers can skip invalid entries.
    """
    name = (name or "").strip()
    if not name:
        return None
    try:
        skill = SkillMaster.objects.filter(name__iexact=name).first()
        if skill:
            return skill
        skill = SkillMaster.objects.create(
            id=uuid.uuid4(),
            name=name,
        )
        return skill
    except IntegrityError:
        # Race condition — another request created it between our filter and create
        return SkillMaster.objects.filter(name__iexact=name).first()


# ---------------------------------------------------------------------------
# Section writers
# ---------------------------------------------------------------------------


def _write_skills(profile: UserProfile, skills: list[dict]) -> None:
    """Create SkillMaster + EmployeeSkill rows for each extracted skill."""
    print(f"\n[AI EXTRACTION] Writing {len(skills)} skills for profile {profile.id}")
    written = 0
    skipped = 0
    for item in skills:
        # Handle both dict format {"name":...} and plain string
        if isinstance(item, str):
            item = {"name": item}
        skill_name = (item.get("name") or "").strip()
        if not skill_name:
            print(f"  [SKILL] SKIP — empty name, raw item: {item}")
            continue

        skill_master = _get_or_create_skill(skill_name)
        if not skill_master:
            print(f"  [SKILL] SKIP — could not get/create SkillMaster for '{skill_name}'")
            continue

        proficiency = _normalize_proficiency(item.get("proficiency", "Intermediate"))
        years = _parse_float(item.get("years"))

        try:
            existing = EmployeeSkill.objects.filter(
                profile=profile, skill=skill_master
            ).first()
            if existing:
                print(f"  [SKILL] SKIP (already exists) — '{skill_name}'")
                skipped += 1
                continue
            EmployeeSkill.objects.create(
                id=uuid.uuid4(),
                profile=profile,
                skill=skill_master,
                proficiency_level=proficiency,
                years_of_experience=years,
                source="ai_extracted",
                confidence_score=None,
                verified_by_hr=False,
                is_primary=False,
            )
            print(f"  [SKILL] SAVED — '{skill_name}' | {proficiency} | {years} yrs")
            written += 1
        except IntegrityError:
            print(f"  [SKILL] SKIP (IntegrityError) — '{skill_name}'")
            skipped += 1
    print(f"[AI EXTRACTION] Skills done: {written} saved, {skipped} skipped")


def _write_experiences(profile: UserProfile, experiences: list[dict]) -> None:
    """Create EmployeeExperience rows for each extracted experience entry."""
    print(f"\n[AI EXTRACTION] Writing {len(experiences)} experiences")
    for item in experiences:
        company = (item.get("company_name") or "").strip()
        designation = (item.get("designation") or "").strip()
        if not company or not designation:
            logger.debug("Skipping experience with missing company/designation: %r", item)
            continue

        start_date = _parse_date(item.get("start_date"))
        if start_date is None:
            # start_date is non-nullable on the model; use a sentinel date
            # rather than crashing so that useful data is not discarded.
            logger.warning(
                "Experience at '%s' has no parseable start_date — using 2000-01-01 sentinel.",
                company,
            )
            start_date = date(2000, 1, 1)

        end_date = _parse_date(item.get("end_date"))
        is_current = bool(item.get("is_current", False))

        try:
            EmployeeExperience.objects.create(
                id=uuid.uuid4(),
                profile=profile,
                company_name=company,
                designation=designation,
                employment_type=(item.get("employment_type") or "")[:50] or None,
                start_date=start_date,
                end_date=end_date,
                is_current=is_current,
                location=(item.get("location") or "")[:255] or None,
                description=item.get("description") or None,
            )
            print(f"  [EXPERIENCE] SAVED — {designation} @ {company}")
        except Exception as exc:
            print(f"  [EXPERIENCE] FAILED — {company}: {exc}")
            logger.warning("Failed to create experience row for '%s': %s", company, exc)


def _write_projects(profile: UserProfile, projects: list[dict]) -> None:
    """Create Project and ProjectSkill rows for each extracted project."""
    print(f"\n[AI EXTRACTION] Writing {len(projects)} projects")
    for item in projects:
        name = (item.get("name") or "").strip()
        if not name:
            continue

        start_date = _parse_date(item.get("start_date"))
        end_date = _parse_date(item.get("end_date"))
        is_current = bool(item.get("is_current", False))

        try:
            project = Project.objects.create(
                id=uuid.uuid4(),
                profile=profile,
                name=name[:255],
                description=item.get("description") or None,
                role=(item.get("role") or "")[:255] or None,
                start_date=start_date,
                end_date=end_date,
                is_current=is_current,
            )
            print(f"  [PROJECT] SAVED — '{name}' | tech: {item.get('tech_stack', [])}")
        except Exception as exc:
            print(f"  [PROJECT] FAILED — '{name}': {exc}")
            logger.warning("Failed to create project row '%s': %s", name, exc)
            continue

        # Associate tech stack skills with the project
        tech_stack: list[str] = item.get("tech_stack") or []
        for tech_name in tech_stack:
            tech_name = (tech_name or "").strip()
            if not tech_name:
                continue
            skill_master = _get_or_create_skill(tech_name)
            if not skill_master:
                continue
            try:
                ProjectSkill.objects.create(
                    id=uuid.uuid4(),
                    project=project,
                    skill=skill_master,
                )
            except IntegrityError:
                logger.debug(
                    "ProjectSkill already exists for project=%s skill=%s — skipping.",
                    project.id,
                    skill_master.id,
                )


def _write_certifications(profile: UserProfile, certifications: list[dict]) -> None:
    """Create Certification rows for each extracted certification."""
    for item in certifications:
        name = (item.get("name") or "").strip()
        if not name:
            continue
        try:
            Certification.objects.create(
                id=uuid.uuid4(),
                profile=profile,
                name=name[:255],
                issuer=(item.get("issuer") or "")[:255] or None,
                issue_date=_parse_date(item.get("issue_date")),
                expiry_date=_parse_date(item.get("expiry_date")),
                credential_url=None,
            )
        except Exception as exc:
            logger.warning("Failed to create certification row '%s': %s", name, exc)


def _write_education(profile: UserProfile, education: list[dict]) -> None:
    """Create Education rows for each extracted education entry."""
    for item in education:
        degree = (item.get("degree") or "").strip()
        institution = (item.get("institution") or "").strip()
        if not degree or not institution:
            continue
        try:
            Education.objects.create(
                id=uuid.uuid4(),
                profile=profile,
                degree=degree[:255],
                institution=institution[:255],
                start_year=_parse_int(item.get("start_year")),
                end_year=_parse_int(item.get("end_year")),
            )
        except Exception as exc:
            logger.warning(
                "Failed to create education row '%s @ %s': %s", degree, institution, exc
            )


def _write_links(profile: UserProfile, data: dict) -> None:
    """
    Save linkedin_url, github_url, and portfolio_url to EmployeeProfile.

    Each field is only written when the LLM returned a non-empty value AND the
    existing profile field is currently blank, so user edits are never overwritten.
    ``emp_profile.save()`` is called only for the fields that actually changed.
    """
    linkedin_url = (data.get("linkedin_url") or "").strip()
    github_url = (data.get("github_url") or "").strip()
    portfolio_url = (data.get("portfolio_url") or "").strip()

    if not any([linkedin_url, github_url, portfolio_url]):
        return

    try:
        emp_profile, _ = EmployeeProfile.objects.get_or_create(
            profile=profile,
            defaults={"id": uuid.uuid4()},
        )
        changed_fields: list[str] = []

        if linkedin_url and not emp_profile.linkedin_url:
            emp_profile.linkedin_url = linkedin_url
            changed_fields.append("linkedin_url")
            print(f"  [LINKS] linkedin_url set: {linkedin_url}")

        if github_url and not emp_profile.github_url:
            emp_profile.github_url = github_url
            changed_fields.append("github_url")
            print(f"  [LINKS] github_url set: {github_url}")

        if portfolio_url and not emp_profile.portfolio_url:
            emp_profile.portfolio_url = portfolio_url
            changed_fields.append("portfolio_url")
            print(f"  [LINKS] portfolio_url set: {portfolio_url}")

        if changed_fields:
            emp_profile.save(update_fields=changed_fields)
            logger.info(
                "Saved link fields %s for profile_id=%s", changed_fields, profile.id
            )
        else:
            logger.debug(
                "No link fields updated for profile_id=%s (all already set or LLM returned null).",
                profile.id,
            )
    except Exception as exc:
        logger.warning("Failed to update EmployeeProfile link fields: %s", exc)


def _write_summary_and_experience(profile: UserProfile, data: dict) -> None:
    """
    Update EmployeeProfile.summary if currently blank.
    Update UserProfile.experience_years if currently None.

    Both fields are only set when empty so AI does not overwrite user edits.
    """
    summary = (data.get("summary") or "").strip()
    total_years = _parse_float(data.get("total_years_experience"))

    # Update EmployeeProfile.summary
    if summary:
        try:
            emp_profile, _ = EmployeeProfile.objects.get_or_create(
                profile=profile,
                defaults={"id": uuid.uuid4()},
            )
            if not emp_profile.summary:
                emp_profile.summary = summary
                emp_profile.save(update_fields=["summary"])
        except Exception as exc:
            logger.warning("Failed to update EmployeeProfile summary: %s", exc)

    # Update UserProfile.experience_years
    if total_years is not None and profile.experience_years is None:
        try:
            profile.experience_years = total_years
            profile.save(update_fields=["experience_years"])
        except Exception as exc:
            logger.warning("Failed to update UserProfile.experience_years: %s", exc)


# ---------------------------------------------------------------------------
# populate_profile — master writer
# ---------------------------------------------------------------------------


def populate_profile(profile: UserProfile, data: dict) -> None:
    """
    Write all sections of extracted resume data into normalised tables.

    Strategy: append-only for list sections (skills, experience, projects,
    certifications, education). Duplicate detection is by unique constraints;
    IntegrityError is caught and silently skipped so existing manually-entered
    data is never destroyed.

    Parameters
    ----------
    profile:
        The UserProfile whose tables will be populated.
    data:
        Parsed extraction dict from ``extractor.extract_profile()``.
    """
    logger.info("Populating profile tables for profile_id=%s", profile.id)

    _write_skills(profile, data.get("skills") or [])
    _write_experiences(profile, data.get("experiences") or [])
    _write_projects(profile, data.get("projects") or [])
    _write_certifications(profile, data.get("certifications") or [])
    _write_education(profile, data.get("education") or [])
    _write_summary_and_experience(profile, data)
    _write_links(profile, data)

    logger.info("Profile population complete for profile_id=%s", profile.id)


# ---------------------------------------------------------------------------
# run_extraction — pipeline entry point
# ---------------------------------------------------------------------------


def run_extraction(resume_upload_id: str) -> dict[str, Any]:
    """
    Run the full AI resume extraction pipeline for a given ResumeUpload.

    Steps
    -----
    1. Load the ResumeUpload row.
    2. Create (or reset) an AIProfileExtraction row with status='processing'.
    3. Download file bytes from Supabase Storage.
    4. Extract plain text from the file bytes.
    5. Call Ollama to extract structured data.
    6. Persist raw_text + extracted_json to AIProfileExtraction.
    7. Write extracted data to normalised profile tables.
    8. Mark extraction_status='completed' on ResumeUpload.
    9. Mark AIProfileExtraction.status='completed'.

    Parameters
    ----------
    resume_upload_id:
        UUID (as string) of the ResumeUpload to process.

    Returns
    -------
    dict
        ``{"status": "completed", "extraction_id": "<uuid>"}``

    Raises
    ------
    ResumeUpload.DoesNotExist
        If the upload row cannot be found.
    ValueError
        On extraction or storage download failure.
    """
    # 1. Load the ResumeUpload
    upload = ResumeUpload.objects.get(id=resume_upload_id)
    profile: UserProfile = upload.profile

    # 2. Create or reuse an AIProfileExtraction row
    extraction, _ = AIProfileExtraction.objects.get_or_create(
        resume_upload=upload,
        profile=profile,
        defaults={
            "id": uuid.uuid4(),
            "status": "processing",
            "model_name": getattr(settings, "OLLAMA_LLM_MODEL", "llama3.2:3b"),
        },
    )
    extraction.status = "processing"
    extraction.model_name = getattr(settings, "OLLAMA_LLM_MODEL", "llama3.2:3b")
    extraction.save(update_fields=["status", "model_name"])

    try:
        # 3. Download file bytes from Supabase Storage
        logger.info(
            "Downloading resume from Supabase Storage: path=%s", upload.storage_path
        )
        supabase = get_supabase_admin_client()
        bucket: str = settings.SUPABASE_STORAGE_BUCKET_RESUMES
        file_bytes: bytes = supabase.storage.from_(bucket).download(upload.storage_path)
        if not file_bytes:
            raise ValueError(
                f"Supabase Storage returned empty bytes for path='{upload.storage_path}'."
            )

        # 4. Extract plain text
        raw_text = text_extractor.extract_text(file_bytes, upload.mime_type)
        if not raw_text or not raw_text.strip():
            raise ValueError(
                "Text extraction produced no content. "
                "The file may be a scanned image or corrupted."
            )
        logger.info(
            "Extracted %d characters of text from resume.", len(raw_text)
        )

        # 5. Call Ollama
        extracted_data = extractor.extract_profile(raw_text)

        # 6. Persist extraction record
        extraction.raw_text = raw_text
        extraction.extracted_json = extracted_data
        extraction.save(update_fields=["raw_text", "extracted_json"])

        # Print full extracted JSON to terminal for debugging
        print("\n" + "="*60)
        print(f"[AI EXTRACTION] Raw text length: {len(raw_text)} chars")
        print(f"[AI EXTRACTION] Full extracted JSON from Ollama:")
        print(json.dumps(extracted_data, indent=2))
        print("="*60 + "\n")

        # 7. Write to normalised tables
        populate_profile(profile, extracted_data)

        # 8. Mark upload as completed
        upload.extraction_status = "completed"
        upload.save(update_fields=["extraction_status"])

        # 9. Mark extraction as completed
        extraction.status = "completed"
        extraction.save(update_fields=["status"])

        logger.info(
            "Extraction completed: extraction_id=%s profile_id=%s",
            extraction.id,
            profile.id,
        )
        return {
            "status": "completed",
            "extraction_id": str(extraction.id),
        }

    except Exception as exc:
        # Mark both rows as failed before re-raising so the view can return
        # a clean error response without an unhandled exception.
        logger.error(
            "Extraction failed for resume_upload_id=%s: %s", resume_upload_id, exc
        )
        try:
            extraction.status = "failed"
            extraction.save(update_fields=["status"])
        except Exception:
            pass
        try:
            upload.extraction_status = "failed"
            upload.save(update_fields=["extraction_status"])
        except Exception:
            pass
        raise
