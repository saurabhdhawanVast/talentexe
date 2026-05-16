from __future__ import annotations

"""
Semantic search pipeline.

Flow:
  1. parse_query  — Ollama LLM extracts structured intent from the NL query
  2. embed query  — Ollama embedding of the raw query text
  3. vector_search — pgvector cosine similarity against employee_embeddings
                     restricted to profile_status='approved'
  4. hard_filters  — deterministic location / min_years / department filters
  5. explain       — delegated to explainer.py for match scores + text
"""

import json
import logging
import re
from typing import Any

import requests
from django.conf import settings
from django.db import connection

logger = logging.getLogger(__name__)

_OLLAMA_TIMEOUT = 120
_DEFAULT_MAX_RESULTS = 20
_MIN_SIMILARITY = 0.45   # drop candidates with cosine similarity below this before LLM scoring
_MIN_MATCH_SCORE = 65    # drop results with LLM match score below this from the final response


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _ollama_url() -> str:
    return getattr(settings, "OLLAMA_BASE_URL", "http://localhost:11434")


def _llm_model() -> str:
    return getattr(settings, "OLLAMA_LLM_MODEL", "llama3.2:3b")


def _max_results() -> int:
    return int(getattr(settings, "SEARCH_MAX_RESULTS", _DEFAULT_MAX_RESULTS))


def _strip_fences(text: str) -> str:
    text = text.strip()
    text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\s*```$", "", text)
    return text.strip()


def _call_llm(prompt: str) -> str:
    url = f"{_ollama_url()}/api/generate"
    payload = {
        "model": _llm_model(),
        "prompt": prompt,
        "stream": False,
        "options": {"temperature": 0.1, "num_predict": 800},
    }
    try:
        resp = requests.post(url, json=payload, timeout=_OLLAMA_TIMEOUT)
    except requests.exceptions.ConnectionError as exc:
        raise ValueError(f"Cannot reach Ollama at {_ollama_url()}.") from exc
    except requests.exceptions.Timeout as exc:
        raise ValueError("Ollama LLM request timed out.") from exc

    if resp.status_code != 200:
        raise ValueError(f"Ollama LLM returned HTTP {resp.status_code}: {resp.text[:300]}")

    return resp.json().get("response", "")


# ---------------------------------------------------------------------------
# Step 1 — Query Parsing
# ---------------------------------------------------------------------------

_QUERY_PARSE_PROMPT = """\
You are an HR search assistant. Extract ONLY what is explicitly mentioned in the query. Do NOT infer or assume anything.

STRICT RULES:
- If a field is not clearly mentioned in the query, set it to null or [].
- skills_required: only skills/technologies explicitly named in the query.
- location: only if a city/region is explicitly named. Otherwise null.
- min_years_experience: only if a number of years is explicitly stated. Otherwise null.
- role_hint: only one of frontend|backend|fullstack|devops|mobile|data if clearly implied. Otherwise null.
- department: only if explicitly named. Otherwise null.
- availability_hint: only if the query mentions bench/unallocated/free. Otherwise null.

Return ONLY a valid JSON object — no markdown, no explanation.

{{
  "skills_required": [],
  "skills_nice_to_have": [],
  "location": null,
  "min_years_experience": null,
  "role_hint": null,
  "department": null,
  "availability_hint": null
}}

Query: {query}

JSON:"""


def parse_query(query: str) -> dict[str, Any]:
    """
    Use the local LLM to extract structured intent from a plain-English HR query.

    Falls back to an empty intent dict on any parse failure so that search
    degrades gracefully to pure vector similarity.
    """
    prompt = _QUERY_PARSE_PROMPT.format(query=query)
    try:
        raw = _call_llm(prompt)
        cleaned = _strip_fences(raw)
        # Find the JSON object boundaries
        start = cleaned.find("{")
        end = cleaned.rfind("}") + 1
        if start == -1 or end == 0:
            raise ValueError("No JSON object found in LLM response.")
        parsed = json.loads(cleaned[start:end])
        # Sanitize — ensure lists are lists, nulls are None
        raw_years = parsed.get("min_years_experience")
        try:
            min_years = float(raw_years) if raw_years not in (None, "", "null") else None
        except (TypeError, ValueError):
            min_years = None

        return {
            "skills_required": [s for s in (parsed.get("skills_required") or []) if s],
            "skills_nice_to_have": [s for s in (parsed.get("skills_nice_to_have") or []) if s],
            "location": parsed.get("location") or None,
            "min_years_experience": min_years,
            "role_hint": parsed.get("role_hint") or None,
            "department": parsed.get("department") or None,
            "availability_hint": parsed.get("availability_hint") or None,
        }
    except Exception as exc:
        logger.warning("parse_query failed (%s) — falling back to empty intent.", exc)
        return {
            "skills_required": [],
            "skills_nice_to_have": [],
            "location": None,
            "min_years_experience": None,
            "role_hint": None,
            "department": None,
            "availability_hint": None,
        }


# ---------------------------------------------------------------------------
# Step 3 — Vector Similarity Search
# ---------------------------------------------------------------------------

_VECTOR_SEARCH_SQL = """
SELECT
    ee.profile_id::text,
    p.full_name,
    p.designation,
    p.department,
    p.location,
    p.experience_years,
    p.profile_status,
    p.avatar_url,
    1 - (ee.embedding <=> %(query_embedding)s::vector) AS similarity
FROM employee_embeddings ee
JOIN profiles p ON p.id = ee.profile_id
WHERE
    p.role = 'employee'
    AND p.is_active = true
    AND p.profile_status = 'approved'
ORDER BY similarity DESC
LIMIT %(limit)s
"""


def _vector_search(query_embedding: list[float], limit: int = 50) -> list[dict]:
    """
    Run pgvector cosine similarity search.

    Returns only approved, active employee profiles ordered by similarity.
    """
    embedding_str = "[" + ",".join(str(v) for v in query_embedding) + "]"
    with connection.cursor() as cursor:
        cursor.execute(
            _VECTOR_SEARCH_SQL,
            {"query_embedding": embedding_str, "limit": limit},
        )
        columns = [col[0] for col in cursor.description]
        rows = cursor.fetchall()

    return [dict(zip(columns, row)) for row in rows]


# ---------------------------------------------------------------------------
# Step 4 — Hard Filters
# ---------------------------------------------------------------------------


def _apply_hard_filters(results: list[dict], parsed: dict) -> list[dict]:
    filtered = results

    location = (parsed.get("location") or "").strip().lower()
    if location:
        filtered = [
            r for r in filtered
            if location in (r.get("location") or "").lower()
        ]

    min_years = parsed.get("min_years_experience")
    if min_years is not None:
        try:
            min_years = float(min_years)
            filtered = [
                r for r in filtered
                if float(r.get("experience_years") or 0) >= min_years
            ]
        except (TypeError, ValueError):
            pass

    department = (parsed.get("department") or "").strip().lower()
    if department:
        filtered = [
            r for r in filtered
            if department in (r.get("department") or "").lower()
        ]

    # Skill hard filter: if required skills are specified, keep only profiles
    # that have at least one of them (case-insensitive substring match).
    skills_required = [s.lower() for s in (parsed.get("skills_required") or []) if s]
    if skills_required:
        def _has_required_skill(r: dict) -> bool:
            profile_skills = [s.lower() for s in (r.get("top_skills") or [])]
            return any(
                any(req in ps or ps in req for ps in profile_skills)
                for req in skills_required
            )
        filtered = [r for r in filtered if _has_required_skill(r)]

    return filtered[: _max_results()]


# ---------------------------------------------------------------------------
# Top-skills lookup helper
# ---------------------------------------------------------------------------


def _fetch_top_skills(profile_ids: list[str], top_n: int = 5) -> dict[str, list[str]]:
    """Return {profile_id: [skill_name, ...]} for a batch of profiles."""
    if not profile_ids:
        return {}

    placeholders = ",".join(["%s"] * len(profile_ids))
    sql = f"""
        SELECT es.profile_id::text, sm.name
        FROM employee_skills es
        JOIN skills_master sm ON sm.id = es.skill_id
        WHERE es.profile_id IN ({placeholders})
        ORDER BY es.is_primary DESC, es.years_of_experience DESC NULLS LAST
    """
    with connection.cursor() as cursor:
        cursor.execute(sql, profile_ids)
        rows = cursor.fetchall()

    result: dict[str, list[str]] = {}
    for profile_id, skill_name in rows:
        bucket = result.setdefault(profile_id, [])
        if len(bucket) < top_n:
            bucket.append(skill_name)
    return result


# ---------------------------------------------------------------------------
# Public orchestrator
# ---------------------------------------------------------------------------


def search(query: str, filters: dict | None = None) -> dict[str, Any]:
    """
    Full semantic search pipeline.

    Returns:
        {
            "query_parsed": { structured intent },
            "results": [ { profile fields, match_score, explanation, top_skills } ],
            "total": int
        }

    Raises ValueError if query is too short or Ollama is unreachable.
    """
    if len(query.strip().split()) < 5:
        raise ValueError(
            "Query too short. Please describe what you're looking for in more detail — "
            "e.g. 'Python backend developer with Django experience' instead of 'python developer'."
        )

    # Step 1 — parse intent
    parsed = parse_query(query)

    # Override parsed fields with any explicit UI filters
    if filters:
        if filters.get("location"):
            parsed["location"] = filters["location"]
        if filters.get("min_years") is not None:
            parsed["min_years_experience"] = filters["min_years"]
        if filters.get("department"):
            parsed["department"] = filters["department"]

    # Step 2 — embed query
    from .embedder import generate_embedding
    try:
        query_embedding = generate_embedding(query)
    except ValueError as exc:
        raise ValueError(f"Embedding failed: {exc}") from exc

    # Step 3 — vector similarity search (top 50 candidates)
    candidates = _vector_search(query_embedding, limit=50)

    if not candidates:
        return {"query_parsed": parsed, "results": [], "total": 0}

    # Drop candidates whose cosine similarity is too low before hitting the LLM
    candidates = [c for c in candidates if (c.get("similarity") or 0) >= _MIN_SIMILARITY]

    if not candidates:
        return {"query_parsed": parsed, "results": [], "total": 0}

    # Attach top skills early so hard filters and explainer can use them
    candidate_ids = [c["profile_id"] for c in candidates]
    top_skills_map = _fetch_top_skills(candidate_ids)
    for c in candidates:
        c["top_skills"] = top_skills_map.get(c["profile_id"], [])

    # Step 4 — hard filters → top 20 (includes skill-match filter)
    filtered = _apply_hard_filters(candidates, parsed)

    if not filtered:
        return {"query_parsed": parsed, "results": [], "total": 0}

    # Step 5 — bulk explanation + scoring
    from .explainer import bulk_explain
    explained = bulk_explain(query, filtered)

    # Drop results the LLM scored as a poor match
    explained = [r for r in explained if r.get("match_score", 0) >= _MIN_MATCH_SCORE]

    if not explained:
        return {"query_parsed": parsed, "results": [], "total": 0}

    # Sort by match_score descending
    explained.sort(key=lambda r: r.get("match_score", 0), reverse=True)

    return {
        "query_parsed": parsed,
        "results": explained,
        "total": len(explained),
    }
