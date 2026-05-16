from __future__ import annotations

"""
Builds a rich plain-text representation of an employee's profile for embedding.

The text is designed to be semantically dense — it includes skill proficiencies,
years of experience, project tech stacks, and work history so that vector
similarity search can match queries like "senior React developer in Mumbai with
fintech experience" even when those exact words don't appear in a single field.
"""

import logging
from typing import Any

from apps.profiles.models import (
    Certification,
    EmployeeExperience,
    EmployeeProfile,
    EmployeeSkill,
    Project,
    ProjectSkill,
    Education,
)
from apps.users.models import UserProfile

logger = logging.getLogger(__name__)


def build_searchable_text(profile: UserProfile) -> str:
    """
    Assemble all profile data into a single string for embedding.

    Returns an empty string if the profile has no meaningful content.
    """
    parts: list[str] = []

    # --- Identity ---
    identity_parts = [profile.full_name]
    if profile.designation:
        identity_parts.append(profile.designation)
    if profile.department:
        identity_parts.append(profile.department)
    parts.append(", ".join(filter(None, identity_parts)))

    if profile.location:
        parts.append(f"Location: {profile.location}")

    if profile.experience_years is not None:
        parts.append(f"Total experience: {profile.experience_years} years")

    # --- Summary ---
    try:
        emp = EmployeeProfile.objects.filter(profile=profile).first()
        if emp and emp.summary:
            parts.append(f"Summary: {emp.summary}")
    except Exception:
        pass

    # --- Skills ---
    try:
        skills = (
            EmployeeSkill.objects.filter(profile=profile)
            .select_related("skill")
            .order_by("-is_primary", "skill__name")
        )
        skill_strs = []
        for es in skills:
            s = f"{es.skill.name} ({es.proficiency_level}"
            if es.years_of_experience is not None:
                s += f", {es.years_of_experience} yrs"
            s += ")"
            skill_strs.append(s)
        if skill_strs:
            parts.append("Skills: " + ", ".join(skill_strs))
    except Exception as exc:
        logger.warning("profile_text_builder: skills error for %s: %s", profile.id, exc)

    # --- Work Experience ---
    try:
        experiences = EmployeeExperience.objects.filter(profile=profile).order_by("-start_date")
        exp_strs = []
        for exp in experiences:
            s = f"{exp.designation} at {exp.company_name}"
            if exp.location:
                s += f" ({exp.location})"
            if exp.description:
                s += f": {exp.description[:200]}"
            exp_strs.append(s)
        if exp_strs:
            parts.append("Work experience: " + " | ".join(exp_strs))
    except Exception as exc:
        logger.warning("profile_text_builder: experience error for %s: %s", profile.id, exc)

    # --- Projects ---
    try:
        projects = Project.objects.filter(profile=profile).prefetch_related("project_skills__skill")
        proj_strs = []
        for proj in projects:
            s = proj.name
            if proj.description:
                s += f": {proj.description[:150]}"
            tech = [ps.skill.name for ps in proj.project_skills.all()]
            if tech:
                s += f" [{', '.join(tech)}]"
            proj_strs.append(s)
        if proj_strs:
            parts.append("Projects: " + " | ".join(proj_strs))
    except Exception as exc:
        logger.warning("profile_text_builder: projects error for %s: %s", profile.id, exc)

    # --- Certifications ---
    try:
        certs = Certification.objects.filter(profile=profile)
        cert_names = [c.name for c in certs if c.name]
        if cert_names:
            parts.append("Certifications: " + ", ".join(cert_names))
    except Exception as exc:
        logger.warning("profile_text_builder: certs error for %s: %s", profile.id, exc)

    # --- Education ---
    try:
        edu_entries = Education.objects.filter(profile=profile).order_by("-end_year")
        edu_strs = [f"{e.degree} from {e.institution}" for e in edu_entries if e.degree]
        if edu_strs:
            parts.append("Education: " + " | ".join(edu_strs))
    except Exception as exc:
        logger.warning("profile_text_builder: education error for %s: %s", profile.id, exc)

    return "\n".join(filter(None, parts))
