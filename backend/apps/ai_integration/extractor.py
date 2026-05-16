from __future__ import annotations

# apps/ai_integration/extractor.py

"""
Ollama LLM client for resume data extraction.

Calls the local Ollama HTTP API (`/api/generate`) with llama3.2:3b.
On JSON parse failure the call is retried once with a stricter prompt.
Connection errors produce a descriptive ValueError rather than a raw
socket traceback propagating to the view layer.
"""

import json
import logging
import re
from typing import Any

import requests
from django.conf import settings

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_OLLAMA_TIMEOUT_SECONDS = 240  # CPU-only inference needs more time

_EXTRACTION_SYSTEM_PROMPT = """You are an expert resume parser. Extract ALL structured information from the resume text below.

RULES:
- Return ONLY a valid JSON object. No markdown, no code fences, no explanation.
- Use null for any field you cannot find. Dates must be YYYY-MM-DD or null.
- Resumes come in many formats — section headers may be in ANY case (Technical Skills, TECHNICAL SKILLS, technical skills, Skills, Core Competencies, Technologies, etc.). Handle all of them.
- Skills: extract every programming language, framework, library, tool, cloud service, or technology mentioned anywhere in the resume — in skills sections, in project descriptions, in job descriptions.
- Projects: extract every project mentioned, whether under Projects, Academic Projects, Personal Projects, or described inside work experience.
- Be thorough. Do not skip sections just because they use an unexpected format or heading style.
- LinkedIn URL: look for linkedin.com links anywhere in the resume (header, contact, summary). Return the full URL or null.
- GitHub URL: look for github.com links anywhere in the resume. Return the full URL or null.
- Portfolio URL: look for a personal website, portfolio, or blog URL that is not github.com, linkedin.com, or a common social network. Return the full URL or null."""

_EXTRACTION_USER_TEMPLATE = """\
Extract this JSON from the resume. Be thorough — extract ALL skills, ALL projects, ALL experience.

{{
  "summary": "<professional summary or objective, or null>",
  "skills": [
    {{"name": "<one skill/language/framework/tool per entry>", "proficiency": "<Beginner|Intermediate|Expert>", "years": <number or null>}}
  ],
  "experiences": [
    {{
      "company_name": "<string>",
      "designation": "<job title>",
      "employment_type": "<Full-time|Part-time|Contract|Internship or null>",
      "start_date": "<YYYY-MM-DD or null>",
      "end_date": "<YYYY-MM-DD or null>",
      "is_current": <true|false>,
      "location": "<string or null>",
      "description": "<string or null>"
    }}
  ],
  "projects": [
    {{
      "name": "<project name>",
      "description": "<what the project does>",
      "role": "<role in project or null>",
      "tech_stack": ["<every technology/language/framework used>"],
      "start_date": "<YYYY-MM-DD or null>",
      "end_date": "<YYYY-MM-DD or null>",
      "is_current": <true|false>
    }}
  ],
  "certifications": [
    {{
      "name": "<certification name>",
      "issuer": "<issuing organization or null>",
      "issue_date": "<YYYY-MM-DD or null>",
      "expiry_date": "<YYYY-MM-DD or null>"
    }}
  ],
  "education": [
    {{
      "degree": "<degree name e.g. B.Tech, B.E., M.Sc>",
      "institution": "<college or university name>",
      "start_year": <number or null>,
      "end_year": <graduation year or null>
    }}
  ],
  "total_years_experience": <total years of work experience as number or null>,
  "linkedin_url": "<full linkedin.com profile URL or null>",
  "github_url": "<full github.com profile URL or null>",
  "portfolio_url": "<personal website or portfolio URL (not linkedin/github) or null>"
}}

Resume:
---
{resume_text}
---

JSON:"""

_STRICT_RETRY_TEMPLATE = """\
Output ONLY the raw JSON object starting with {{ and ending with }}. No markdown. No explanation.

Important: Extract ALL skills, ALL experiences (company, designation, dates), and ALL projects.

Resume:
---
{resume_text}
---

JSON:"""


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _get_ollama_url() -> str:
    """Read OLLAMA_BASE_URL from Django settings with fallback."""
    return getattr(settings, "OLLAMA_BASE_URL", "http://localhost:11434")


def _get_model_name() -> str:
    """Read OLLAMA_LLM_MODEL from Django settings with fallback."""
    return getattr(settings, "OLLAMA_LLM_MODEL", "llama3.2:3b")


def _strip_code_fences(text: str) -> str:
    """
    Remove markdown code fences that LLMs sometimes wrap JSON in.

    Handles:
        ```json { ... } ```
        ``` { ... } ```
        plain { ... }
    """
    text = text.strip()
    # Remove opening fence (```json or ```)
    text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.IGNORECASE)
    # Remove closing fence
    text = re.sub(r"\s*```$", "", text)
    return text.strip()


def _call_ollama(prompt: str) -> str:
    """
    POST to the Ollama /api/generate endpoint and return the response text.

    Raises
    ------
    ValueError
        If Ollama is unreachable, returns a non-200 status, or the response
        body cannot be decoded.
    """
    base_url = _get_ollama_url()
    model = _get_model_name()
    url = f"{base_url}/api/generate"

    payload: dict[str, Any] = {
        "model": model,
        "prompt": prompt,
        "stream": False,
        "options": {
            "temperature": 0.1,   # low temperature for deterministic extraction
            "num_predict": 3000,  # enough for full JSON including all experiences/projects
        },
    }

    try:
        response = requests.post(url, json=payload, timeout=_OLLAMA_TIMEOUT_SECONDS)
    except requests.exceptions.ConnectionError as exc:
        raise ValueError(
            f"Cannot reach Ollama at {base_url}. "
            "Ensure Ollama is running (`ollama serve`) and the model is pulled "
            f"(`ollama pull {model}`). Original error: {exc}"
        ) from exc
    except requests.exceptions.Timeout as exc:
        raise ValueError(
            f"Ollama request timed out after {_OLLAMA_TIMEOUT_SECONDS}s. "
            "The resume may be too long or the model is under load."
        ) from exc
    except requests.exceptions.RequestException as exc:
        raise ValueError(f"Ollama HTTP request failed: {exc}") from exc

    if response.status_code != 200:
        raise ValueError(
            f"Ollama returned HTTP {response.status_code}: {response.text[:500]}"
        )

    try:
        body = response.json()
    except json.JSONDecodeError as exc:
        raise ValueError(f"Ollama response is not valid JSON: {exc}") from exc

    raw_text: str = body.get("response", "")
    if not raw_text:
        raise ValueError("Ollama returned an empty 'response' field.")

    return raw_text


def _parse_json_from_text(raw_text: str) -> dict[str, Any]:
    """
    Attempt to parse a JSON object from LLM output.

    Strategy:
    1. Strip code fences.
    2. Try to parse the whole string.
    3. If that fails, locate the first '{' and last '}' and parse the slice.

    Raises json.JSONDecodeError if all strategies fail.
    """
    cleaned = _strip_code_fences(raw_text)

    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pass

    # Heuristic: find the outermost { ... } block
    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start != -1 and end != -1 and end > start:
        try:
            return json.loads(cleaned[start : end + 1])
        except json.JSONDecodeError:
            pass

    raise json.JSONDecodeError("No valid JSON object found in LLM output", cleaned, 0)


# ---------------------------------------------------------------------------
# Text preprocessing
# ---------------------------------------------------------------------------

_SKILL_SECTION_RE = re.compile(
    r"^(technical\s+skills?|skills?|core\s+competencies|technologies|tools?|"
    r"expertise|programming\s+languages?|frameworks?|tech\s+stack|languages?\s+&\s+tools?|"
    r"key\s+skills?|it\s+skills?|software\s+skills?)",
    re.IGNORECASE,
)

_PROJECT_SECTION_RE = re.compile(
    r"^(projects?|software\s+engineering\s+projects?|academic\s+projects?|"
    r"personal\s+projects?|work\s+samples?|key\s+projects?|notable\s+projects?)",
    re.IGNORECASE,
)

_EXPERIENCE_SECTION_RE = re.compile(
    r"^(work\s+experience|professional\s+experience|experience|employment(\s+history)?|"
    r"career\s+history|work\s+history)",
    re.IGNORECASE,
)

_DEPRIORITIZE_RE = re.compile(
    r"^(education|academic|certifications?|awards?|achievements?|references?|"
    r"hobbies|interests?|languages?|declaration)",
    re.IGNORECASE,
)


def _prioritize_skills_section(text: str) -> str:
    """
    Reorder resume text so skills, projects, and experience appear before
    low-value sections (education, references, etc.), surviving the character
    truncation cutoff.
    Order: intro → skills → projects → experience → rest
    Falls back to original text if no recognizable sections found.
    """
    lines = text.splitlines(keepends=True)
    sections: dict[str, list[str]] = {
        "intro": [], "skills": [], "projects": [], "experience": [], "rest": []
    }
    current = "intro"

    for line in lines:
        stripped = line.strip()
        if _SKILL_SECTION_RE.match(stripped):
            current = "skills"
        elif _PROJECT_SECTION_RE.match(stripped):
            current = "projects"
        elif _EXPERIENCE_SECTION_RE.match(stripped):
            current = "experience"
        elif _DEPRIORITIZE_RE.match(stripped):
            current = "rest"
        sections[current].append(line)

    if sections["skills"] or sections["projects"] or sections["experience"]:
        reordered = (
            sections["intro"]
            + sections["skills"]
            + sections["projects"]
            + sections["experience"]
            + sections["rest"]
        )
        return "".join(reordered)

    return text


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def extract_profile(raw_text: str) -> dict[str, Any]:
    """
    Send resume text to Ollama and return the extracted profile as a dict.

    The function builds a structured prompt, calls llama3.2:3b, parses the
    JSON response, and retries once with a stricter prompt on JSON parse
    failure.

    Parameters
    ----------
    raw_text:
        Plain text content of the resume (already extracted from file bytes).

    Returns
    -------
    dict
        Parsed extraction result matching the schema described in the prompt.

    Raises
    ------
    ValueError
        If Ollama is unreachable, the model fails, or JSON parsing fails
        after the retry.
    """
    if not raw_text or not raw_text.strip():
        raise ValueError("resume text is empty — cannot extract profile data.")

    # 12000 chars (~3000 tokens) captures full resume including skills, projects, and experience.
    # Reorder so skills/projects/experience come before low-value sections like references.
    truncated_text = _prioritize_skills_section(raw_text)[:12_000]

    # --- First attempt ---
    first_prompt = _EXTRACTION_USER_TEMPLATE.format(resume_text=truncated_text)
    full_first_prompt = f"{_EXTRACTION_SYSTEM_PROMPT}\n\n{first_prompt}"

    logger.info("Sending resume to Ollama model '%s' for extraction.", _get_model_name())
    raw_response = _call_ollama(full_first_prompt)
    logger.debug("Ollama raw response (first attempt): %s", raw_response[:500])

    try:
        result = _parse_json_from_text(raw_response)
        logger.info("Ollama extraction succeeded on first attempt.")
        return result
    except json.JSONDecodeError as first_exc:
        logger.warning(
            "JSON parse failed on first attempt (%s). Retrying with strict prompt.",
            first_exc,
        )

    # --- Retry with strict prompt ---
    retry_prompt = _STRICT_RETRY_TEMPLATE.format(resume_text=truncated_text)
    raw_retry_response = _call_ollama(retry_prompt)
    logger.debug("Ollama raw response (retry): %s", raw_retry_response[:500])

    try:
        result = _parse_json_from_text(raw_retry_response)
        logger.info("Ollama extraction succeeded on retry.")
        return result
    except json.JSONDecodeError as retry_exc:
        raise ValueError(
            f"Ollama returned invalid JSON after two attempts. "
            f"Last parse error: {retry_exc}. "
            f"Last raw response (first 500 chars): {raw_retry_response[:500]}"
        ) from retry_exc
