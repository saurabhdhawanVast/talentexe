from __future__ import annotations

# apps/profiles/pdf.py

"""
PDF generation for employee profile download.

Uses ReportLab (pure-Python) to build a clean A4 profile PDF.
Accepts normalised ORM objects from the relational tables.
"""

from io import BytesIO
from typing import Any

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    HRFlowable,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

# ---------------------------------------------------------------------------
# Colour palette
# ---------------------------------------------------------------------------

_BRAND   = colors.HexColor("#1a4f8a")
_LIGHT   = colors.HexColor("#e8f0fe")
_GREY    = colors.HexColor("#555555")
_BORDER  = colors.HexColor("#dddddd")
_WHITE   = colors.white
_BLACK   = colors.HexColor("#222222")

# ---------------------------------------------------------------------------
# Styles
# ---------------------------------------------------------------------------

_base = getSampleStyleSheet()

_H1 = ParagraphStyle(
    "H1", fontName="Helvetica-Bold", fontSize=18, textColor=_BRAND,
    spaceAfter=2, leading=22,
)
_H2 = ParagraphStyle(
    "H2", fontName="Helvetica-Bold", fontSize=11, textColor=_BRAND,
    spaceBefore=10, spaceAfter=4, leading=14,
)
_BODY = ParagraphStyle(
    "Body", fontName="Helvetica", fontSize=9, textColor=_BLACK,
    leading=13, spaceAfter=3,
)
_SMALL = ParagraphStyle(
    "Small", fontName="Helvetica", fontSize=8.5, textColor=_GREY,
    leading=12, spaceAfter=2,
)
_BOLD_SMALL = ParagraphStyle(
    "BoldSmall", fontName="Helvetica-Bold", fontSize=9, textColor=_BLACK,
    leading=13,
)
_LINK = ParagraphStyle(
    "Link", fontName="Helvetica", fontSize=8.5, textColor=_BRAND, leading=12,
)


def _s(value: Any) -> str:
    """Return str(value) or empty string for None."""
    return "" if value is None else str(value)


def _p(text: str, style: ParagraphStyle = _BODY) -> Paragraph:
    return Paragraph(text or "", style)


def _section(story: list, title: str) -> None:
    story.append(Spacer(1, 4))
    story.append(_p(title, _H2))
    story.append(HRFlowable(width="100%", thickness=1, color=_BRAND, spaceAfter=4))


# ---------------------------------------------------------------------------
# Section builders
# ---------------------------------------------------------------------------


def _build_skills(story: list, skills: list[Any]) -> None:
    _section(story, "Skills")
    if not skills:
        story.append(_p("No skills listed.", _SMALL))
        return

    rows = [
        [
            _p("<b>Skill</b>", _BOLD_SMALL),
            _p("<b>Proficiency</b>", _BOLD_SMALL),
            _p("<b>Years</b>", _BOLD_SMALL),
        ]
    ]
    for es in skills:
        rows.append([
            _p(_s(es.skill.name)),
            _p(_s(es.proficiency_level)),
            _p(_s(es.years_of_experience) if es.years_of_experience else "—"),
        ])

    t = Table(rows, colWidths=[90 * mm, 50 * mm, 30 * mm])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), _BRAND),
        ("TEXTCOLOR",  (0, 0), (-1, 0), _WHITE),
        ("FONTNAME",   (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE",   (0, 0), (-1, -1), 8.5),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [_WHITE, _LIGHT]),
        ("GRID",       (0, 0), (-1, -1), 0.4, _BORDER),
        ("VALIGN",     (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    story.append(t)


def _build_experience(story: list, experiences: list[Any]) -> None:
    _section(story, "Work Experience")
    if not experiences:
        story.append(_p("No experience listed.", _SMALL))
        return

    for exp in experiences:
        date_range = _s(exp.start_date)
        if exp.is_current:
            date_range += " — Present"
        elif exp.end_date:
            date_range += f" — {_s(exp.end_date)}"

        loc = f", {_s(exp.location)}" if exp.location else ""
        story.append(_p(f"<b>{_s(exp.designation)}</b> · {_s(exp.company_name)}{loc}", _BOLD_SMALL))
        story.append(_p(date_range, _SMALL))
        if exp.description:
            story.append(_p(_s(exp.description), _BODY))
        story.append(Spacer(1, 4))


def _build_projects(story: list, projects: list[Any]) -> None:
    _section(story, "Projects")
    if not projects:
        story.append(_p("No projects listed.", _SMALL))
        return

    for proj in projects:
        client = f" · Client: {_s(proj.client_name)}" if proj.client_name else ""
        role = f" · Role: {_s(proj.role)}" if proj.role else ""
        story.append(_p(f"<b>{_s(proj.name)}</b>{client}{role}", _BOLD_SMALL))
        if proj.description:
            story.append(_p(_s(proj.description), _BODY))
        tech = [ps.skill.name for ps in proj.project_skills.all()]
        if tech:
            story.append(_p("Tech: " + ", ".join(tech), _SMALL))
        story.append(Spacer(1, 4))


def _build_certifications(story: list, certifications: list[Any]) -> None:
    _section(story, "Certifications")
    if not certifications:
        story.append(_p("No certifications listed.", _SMALL))
        return

    for cert in certifications:
        issuer = f" — {_s(cert.issuer)}" if cert.issuer else ""
        date = f" ({_s(cert.issue_date)})" if cert.issue_date else ""
        story.append(_p(f"<b>{_s(cert.name)}</b>{issuer}{date}", _BODY))


def _build_education(story: list, education: list[Any]) -> None:
    _section(story, "Education")
    if not education:
        story.append(_p("No education listed.", _SMALL))
        return

    for edu in education:
        years = ""
        if edu.start_year and edu.end_year:
            years = f" ({edu.start_year}–{edu.end_year})"
        elif edu.end_year:
            years = f" ({edu.end_year})"
        grade = f" · Grade: {_s(edu.grade)}" if edu.grade else ""
        story.append(_p(f"<b>{_s(edu.degree)}</b> — {_s(edu.institution)}{years}{grade}", _BODY))


def _build_languages(story: list, languages: list[Any]) -> None:
    if not languages:
        return
    _section(story, "Languages")
    parts = []
    for lang in languages:
        if isinstance(lang, dict):
            name = lang.get("name", "")
            prof = lang.get("proficiency", "")
            parts.append(f"{name} ({prof})" if prof else name)
        else:
            parts.append(str(lang))
    story.append(_p(", ".join(parts), _BODY))


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------


def generate_profile_pdf(
    user: Any,
    employee: Any | None,
    skills: list[Any] | None = None,
    experiences: list[Any] | None = None,
    projects: list[Any] | None = None,
    certifications: list[Any] | None = None,
    education: list[Any] | None = None,
) -> bytes:
    """
    Render a full employee profile to PDF bytes using ReportLab.
    """
    buf = BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=A4,
        leftMargin=18 * mm,
        rightMargin=18 * mm,
        topMargin=20 * mm,
        bottomMargin=20 * mm,
        title=f"Profile — {_s(user.full_name)}",
    )

    story: list = []

    # ── Header ────────────────────────────────────────────────────────────
    story.append(_p(_s(user.full_name), _H1))

    meta_parts = [_s(user.designation), _s(user.department), _s(user.location)]
    meta = " · ".join(p for p in meta_parts if p)
    if meta:
        story.append(_p(meta, _SMALL))

    contact_parts = [f"Email: {_s(user.email)}"]
    if user.phone:
        contact_parts.append(f"Phone: {_s(user.phone)}")
    if user.experience_years:
        contact_parts.append(f"Experience: {_s(user.experience_years)} yrs")
    story.append(_p("  ·  ".join(contact_parts), _SMALL))

    if employee:
        links = []
        if employee.linkedin_url:
            links.append(f'LinkedIn: <link href="{_s(employee.linkedin_url)}">{_s(employee.linkedin_url)}</link>')
        if employee.github_url:
            links.append(f'GitHub: <link href="{_s(employee.github_url)}">{_s(employee.github_url)}</link>')
        if employee.portfolio_url:
            links.append(f'Portfolio: <link href="{_s(employee.portfolio_url)}">{_s(employee.portfolio_url)}</link>')
        if links:
            story.append(_p("  ·  ".join(links), _LINK))

    story.append(Spacer(1, 4))
    story.append(HRFlowable(width="100%", thickness=1.5, color=_BRAND))

    # ── Summary ───────────────────────────────────────────────────────────
    summary = (employee.summary or "") if employee else ""
    if summary:
        _section(story, "Summary")
        story.append(_p(summary, _BODY))

    # ── Sections ──────────────────────────────────────────────────────────
    _build_skills(story, skills or [])
    _build_experience(story, experiences or [])
    _build_projects(story, projects or [])
    _build_education(story, education or [])
    _build_certifications(story, certifications or [])
    _build_languages(story, (employee.languages or []) if employee else [])

    doc.build(story)
    return buf.getvalue()
