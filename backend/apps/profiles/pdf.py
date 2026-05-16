from __future__ import annotations

# apps/profiles/pdf.py

"""
PDF generation for employee profile download.

Uses WeasyPrint to render an inline HTML/CSS template to PDF bytes.
Accepts normalised ORM objects from the relational tables introduced in
Phase 2.1 (EmployeeSkill, EmployeeExperience, Project, Certification,
Education) rather than JSONB lists.
"""

import html
from typing import Any


def _esc(value: Any) -> str:
    """HTML-escape a value; convert None to empty string."""
    if value is None:
        return ""
    return html.escape(str(value))


def _skill_rows(skills: list[Any]) -> str:
    """
    Render ``<tr>`` rows for the skills table.

    Each item is an ``EmployeeSkill`` ORM instance with a related ``skill``
    (``SkillMaster``).
    """
    if not skills:
        return "<tr><td colspan='3'>No skills listed.</td></tr>"
    rows = []
    for es in skills:
        rows.append(
            f"<tr><td>{_esc(es.skill.name)}</td>"
            f"<td>{_esc(es.proficiency_level)}</td>"
            f"<td>{_esc(es.years_of_experience)}</td></tr>"
        )
    return "".join(rows)


def _experience_items(experiences: list[Any]) -> str:
    """Render ``<li>`` items for work experience entries."""
    if not experiences:
        return "<li>No experience listed.</li>"
    items = []
    for exp in experiences:
        date_range = _esc(exp.start_date)
        if exp.is_current:
            date_range += " — Present"
        elif exp.end_date:
            date_range += f" — {_esc(exp.end_date)}"
        location_part = f", {_esc(exp.location)}" if exp.location else ""
        items.append(
            f"<li><strong>{_esc(exp.designation)}</strong> at {_esc(exp.company_name)}"
            f"{location_part} ({date_range})"
            + (f"<br/><em>{_esc(exp.description)}</em>" if exp.description else "")
            + "</li>"
        )
    return "".join(items)


def _project_items(projects: list[Any]) -> str:
    """Render ``<li>`` items for project entries (with skill badges)."""
    if not projects:
        return "<li>No projects listed.</li>"
    items = []
    for proj in projects:
        skill_badges = "".join(
            f'<span class="badge">{_esc(ps.skill.name)}</span>'
            for ps in proj.project_skills.all()
        )
        client_part = f" | Client: {_esc(proj.client_name)}" if proj.client_name else ""
        role_part = f" | Role: {_esc(proj.role)}" if proj.role else ""
        items.append(
            f"<li><strong>{_esc(proj.name)}</strong>{client_part}{role_part}"
            + (f"<br/>{_esc(proj.description)}" if proj.description else "")
            + (f"<br/>{skill_badges}" if skill_badges else "")
            + "</li>"
        )
    return "".join(items)


def _certification_items(certifications: list[Any]) -> str:
    """Render ``<li>`` items for certification entries."""
    if not certifications:
        return "<li>No certifications listed.</li>"
    items = []
    for cert in certifications:
        issuer_part = f" — {_esc(cert.issuer)}" if cert.issuer else ""
        date_part = f" ({_esc(cert.issue_date)})" if cert.issue_date else ""
        items.append(f"<li>{_esc(cert.name)}{issuer_part}{date_part}</li>")
    return "".join(items)


def _education_items(education: list[Any]) -> str:
    """Render ``<li>`` items for education entries."""
    if not education:
        return "<li>No education listed.</li>"
    items = []
    for edu in education:
        year_range = ""
        if edu.start_year and edu.end_year:
            year_range = f" ({edu.start_year}–{edu.end_year})"
        elif edu.end_year:
            year_range = f" ({edu.end_year})"
        grade_part = f" | Grade: {_esc(edu.grade)}" if edu.grade else ""
        items.append(
            f"<li>{_esc(edu.degree)} — {_esc(edu.institution)}{year_range}{grade_part}</li>"
        )
    return "".join(items)


def _language_items(languages: list[Any]) -> str:
    """Render ``<li>`` items for language entries (still stored as JSONB dicts)."""
    if not languages:
        return "<li>None listed.</li>"
    items = []
    for lang in languages:
        if isinstance(lang, dict):
            name = lang.get("name", "")
            proficiency = lang.get("proficiency", "")
        else:
            name = str(lang)
            proficiency = ""
        parts = [_esc(name)]
        if proficiency:
            parts.append(_esc(proficiency))
        items.append(f"<li>{' — '.join(parts)}</li>")
    return "".join(items)


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
    Render a full employee profile to PDF bytes.

    Parameters
    ----------
    user:
        A ``UserProfile`` model instance.
    employee:
        An ``EmployeeProfile`` model instance, or ``None`` if not yet created.
    skills:
        List of ``EmployeeSkill`` instances (with ``skill`` FK pre-fetched).
    experiences:
        List of ``EmployeeExperience`` instances.
    projects:
        List of ``Project`` instances (with ``project_skills__skill`` pre-fetched).
    certifications:
        List of ``Certification`` instances.
    education:
        List of ``Education`` instances.

    Returns
    -------
    bytes
        Raw PDF binary content ready to be served as ``application/pdf``.
    """
    from weasyprint import CSS, HTML  # noqa: PLC0415 — optional heavy dep

    _skills: list[Any] = skills or []
    _experiences: list[Any] = experiences or []
    _projects: list[Any] = projects or []
    _certs: list[Any] = certifications or []
    _education: list[Any] = education or []
    _languages: list[Any] = (getattr(employee, "languages", None) or []) if employee else []

    summary: str = _esc(getattr(employee, "summary", "")) if employee else ""
    linkedin: str = _esc(getattr(employee, "linkedin_url", "")) if employee else ""
    github: str = _esc(getattr(employee, "github_url", "")) if employee else ""
    portfolio: str = _esc(getattr(employee, "portfolio_url", "")) if employee else ""

    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"/>
<title>Employee Profile — {_esc(user.full_name)}</title>
<style>
  @page {{
    size: A4;
    margin: 20mm 18mm 20mm 18mm;
  }}
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{
    font-family: "Helvetica Neue", Helvetica, Arial, sans-serif;
    font-size: 10pt;
    color: #222;
    line-height: 1.5;
  }}
  h1 {{ font-size: 20pt; color: #1a4f8a; margin-bottom: 2px; }}
  h2 {{
    font-size: 12pt;
    color: #1a4f8a;
    border-bottom: 1.5px solid #1a4f8a;
    padding-bottom: 3px;
    margin-top: 14px;
    margin-bottom: 6px;
  }}
  .header {{ margin-bottom: 10px; }}
  .meta {{ color: #555; font-size: 9pt; margin-top: 4px; }}
  .meta span {{ margin-right: 16px; }}
  .links {{ margin-top: 4px; font-size: 9pt; color: #555; }}
  .links a {{ color: #1a4f8a; text-decoration: none; margin-right: 14px; }}
  table {{
    width: 100%;
    border-collapse: collapse;
    margin-top: 4px;
    font-size: 9.5pt;
  }}
  th {{
    background: #1a4f8a;
    color: white;
    padding: 5px 8px;
    text-align: left;
    font-weight: bold;
  }}
  td {{ padding: 4px 8px; border-bottom: 0.5px solid #ddd; vertical-align: top; }}
  tr:nth-child(even) td {{ background: #f7f9fc; }}
  ul {{ padding-left: 18px; margin-top: 4px; }}
  ul li {{ margin-bottom: 6px; }}
  p {{ margin-top: 4px; }}
  .section {{ margin-bottom: 4px; }}
  .badge {{
    display: inline-block;
    background: #e8f0fe;
    color: #1a4f8a;
    border-radius: 4px;
    padding: 1px 7px;
    font-size: 8.5pt;
    margin: 2px 3px 2px 0;
  }}
</style>
</head>
<body>

<div class="header">
  <h1>{_esc(user.full_name)}</h1>
  <div class="meta">
    <span>{_esc(user.designation)}</span>
    <span>{_esc(user.department)}</span>
    <span>{_esc(user.location)}</span>
  </div>
  <div class="meta">
    <span>Email: {_esc(user.email)}</span>
    {'<span>Phone: ' + _esc(user.phone) + '</span>' if user.phone else ''}
    {'<span>Experience: ' + _esc(user.experience_years) + ' yrs</span>' if user.experience_years else ''}
  </div>
  {'<div class="links">' +
    ('<a href="' + linkedin + '">' + linkedin + '</a>' if linkedin else '') +
    ('<a href="' + github + '">' + github + '</a>' if github else '') +
    ('<a href="' + portfolio + '">' + portfolio + '</a>' if portfolio else '') +
   '</div>'
   if (linkedin or github or portfolio) else ''}
</div>

{'<h2>Summary</h2><p>' + summary + '</p>' if summary else ''}

<h2>Skills</h2>
<table>
  <thead>
    <tr><th>Skill</th><th>Proficiency</th><th>Years</th></tr>
  </thead>
  <tbody>
    {_skill_rows(_skills)}
  </tbody>
</table>

{'<h2>Languages</h2><ul>' + _language_items(_languages) + '</ul>' if _languages else ''}

<h2>Experience</h2>
<ul>
  {_experience_items(_experiences)}
</ul>

<h2>Projects</h2>
<ul>
  {_project_items(_projects)}
</ul>

<h2>Education</h2>
<ul>
  {_education_items(_education)}
</ul>

<h2>Certifications</h2>
<ul>
  {_certification_items(_certs)}
</ul>

</body>
</html>"""

    pdf_bytes: bytes = HTML(string=html_content).write_pdf(
        stylesheets=[CSS(string="")]
    )
    return pdf_bytes
