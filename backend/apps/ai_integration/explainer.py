from __future__ import annotations

"""
Match explanation and scoring.

Uses the local Ollama LLM to generate plain-English explanations and
match scores (0-100) for each search result. A single bulk prompt is
sent for up to 20 profiles to minimise round-trip latency.

On any LLM or parse failure, a fallback score derived from cosine
similarity is used and the explanation is a short generic message.
"""

import json
import logging
import re
from typing import Any

import requests
from django.conf import settings

logger = logging.getLogger(__name__)

_OLLAMA_TIMEOUT = 180  # bulk call with up to 20 profiles


def _ollama_url() -> str:
    return getattr(settings, "OLLAMA_BASE_URL", "http://localhost:11434")


def _llm_model() -> str:
    return getattr(settings, "OLLAMA_LLM_MODEL", "llama3.2:3b")


def _strip_fences(text: str) -> str:
    text = text.strip()
    text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\s*```$", "", text)
    return text.strip()


_BULK_EXPLAIN_PROMPT = """\
You are an HR talent assistant. For each candidate profile listed below, given the HR search query, provide:
1. match_score: an integer 0-100 reflecting how well the candidate fits the query
   - 90-100: matches all key skills + location + experience requirements
   - 70-89:  matches most key skills, minor gaps
   - 50-69:  partial match, some relevant experience
   - below 50: weak match
2. explanation: 1-2 sentences, specific — mention actual skills, years, and project types from the profile

Return ONLY a valid JSON array. No markdown, no extra text.

Format:
[
  {{"profile_id": "<id>", "match_score": <0-100>, "explanation": "<1-2 sentences>"}},
  ...
]

Search query: {query}

Candidates:
{profiles_text}

JSON array:"""


def _build_profiles_text(profiles: list[dict]) -> str:
    lines: list[str] = []
    for i, p in enumerate(profiles, 1):
        parts = [
            f"[{i}] profile_id={p['profile_id']}",
            f"Name: {p.get('full_name', 'Unknown')}",
        ]
        if p.get("designation"):
            parts.append(f"Role: {p['designation']}")
        if p.get("department"):
            parts.append(f"Dept: {p['department']}")
        if p.get("location"):
            parts.append(f"Location: {p['location']}")
        if p.get("experience_years") is not None:
            parts.append(f"Experience: {p['experience_years']} yrs")
        if p.get("top_skills"):
            parts.append(f"Skills: {', '.join(p['top_skills'])}")
        lines.append(" | ".join(parts))
    return "\n".join(lines)


def _similarity_to_score(similarity: float | None) -> int:
    if similarity is None:
        return 50
    return min(100, max(0, int(similarity * 100)))


def bulk_explain(query: str, profiles: list[dict]) -> list[dict]:
    """
    Generate match scores and explanations for a batch of search result profiles.

    Mutates each profile dict in-place by adding 'match_score' and 'explanation',
    then returns the list. Falls back to similarity-based scores on LLM failure.
    """
    if not profiles:
        return profiles

    profiles_text = _build_profiles_text(profiles)
    prompt = _BULK_EXPLAIN_PROMPT.format(query=query, profiles_text=profiles_text)

    url = f"{_ollama_url()}/api/generate"
    payload = {
        "model": _llm_model(),
        "prompt": prompt,
        "stream": False,
        "options": {"temperature": 0.2, "num_predict": 1500},
    }

    id_to_profile = {p["profile_id"]: p for p in profiles}

    try:
        resp = requests.post(url, json=payload, timeout=_OLLAMA_TIMEOUT)
        if resp.status_code != 200:
            raise ValueError(f"Ollama returned HTTP {resp.status_code}")

        raw = resp.json().get("response", "")
        cleaned = _strip_fences(raw)

        # Extract JSON array
        start = cleaned.find("[")
        end = cleaned.rfind("]") + 1
        if start == -1 or end == 0:
            raise ValueError("No JSON array in LLM response.")

        explanations: list[dict] = json.loads(cleaned[start:end])

        for item in explanations:
            pid = str(item.get("profile_id", ""))
            if pid in id_to_profile:
                id_to_profile[pid]["match_score"] = int(item.get("match_score", 50))
                id_to_profile[pid]["explanation"] = str(item.get("explanation", ""))

    except Exception as exc:
        logger.warning("bulk_explain LLM call failed (%s) — falling back to similarity scores.", exc)
        for p in profiles:
            if "match_score" not in p:
                p["match_score"] = _similarity_to_score(p.get("similarity"))
            if "explanation" not in p:
                name = p.get("full_name", "This candidate")
                role = p.get("designation", "")
                exp = p.get("experience_years")
                parts = [name]
                if role:
                    parts.append(f"works as {role}")
                if exp:
                    parts.append(f"with {exp} years of experience")
                p["explanation"] = " ".join(parts) + "."

    # Guarantee both fields exist on every result
    for p in profiles:
        p.setdefault("match_score", _similarity_to_score(p.get("similarity")))
        p.setdefault("explanation", f"{p.get('full_name', 'Candidate')} matched your query.")

    return profiles
