from __future__ import annotations

"""
Ollama embedding wrapper.

Generates 3072-dim vectors using llama3.2:3b via the Ollama /api/embeddings
endpoint. The same model is used for both profile embeddings (stored in
employee_embeddings) and query embeddings (generated at search time).
"""

import logging

import requests
from django.conf import settings

logger = logging.getLogger(__name__)

_TIMEOUT = 60


def _base_url() -> str:
    return getattr(settings, "OLLAMA_BASE_URL", "http://localhost:11434")


def _model() -> str:
    return getattr(settings, "OLLAMA_EMBED_MODEL", getattr(settings, "OLLAMA_LLM_MODEL", "llama3.2:3b"))


def generate_embedding(text: str) -> list[float]:
    """
    Convert text to a 3072-dim float vector via Ollama.

    Raises ValueError if Ollama is unreachable or returns an error.
    """
    if not text or not text.strip():
        raise ValueError("Cannot embed empty text.")

    url = f"{_base_url()}/api/embeddings"
    try:
        resp = requests.post(
            url,
            json={"model": _model(), "prompt": text.strip()},
            timeout=_TIMEOUT,
        )
    except requests.exceptions.ConnectionError as exc:
        raise ValueError(
            f"Cannot reach Ollama at {_base_url()}. Ensure 'ollama serve' is running."
        ) from exc
    except requests.exceptions.Timeout as exc:
        raise ValueError("Ollama embedding request timed out.") from exc

    if resp.status_code != 200:
        raise ValueError(f"Ollama embedding returned HTTP {resp.status_code}: {resp.text[:300]}")

    embedding: list[float] = resp.json().get("embedding", [])
    if not embedding:
        raise ValueError("Ollama returned an empty embedding vector.")

    logger.debug("Generated embedding: %d dims for %d chars of text.", len(embedding), len(text))
    return embedding
