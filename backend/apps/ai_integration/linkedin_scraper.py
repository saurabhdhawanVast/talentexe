from __future__ import annotations

# apps/ai_integration/linkedin_scraper.py

"""
LinkedIn profile page fetcher and text extractor.

Fetches a public LinkedIn profile URL and returns visible plain text
suitable for passing to the Ollama extraction pipeline.

Uses only Python stdlib html.parser (no BeautifulSoup dependency).
Also extracts JSON-LD structured data that LinkedIn embeds for SEO,
which often contains the cleanest structured profile information.
"""

import json
import logging
import re
from html.parser import HTMLParser

import requests

logger = logging.getLogger(__name__)

_TIMEOUT_SECONDS = 15

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
    "Cache-Control": "max-age=0",
}


class _HTMLTextExtractor(HTMLParser):
    """
    Minimal HTML parser that strips tags and collects visible text nodes.

    Tags in _SKIP_TAGS (and their entire subtrees) are ignored so that
    JavaScript, CSS, and metadata do not pollute the extracted text.
    """

    _SKIP_TAGS = frozenset({"script", "style", "noscript", "meta", "link", "head"})

    def __init__(self) -> None:
        super().__init__()
        self._skip_depth: int = 0
        self.texts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list) -> None:
        if tag.lower() in self._SKIP_TAGS:
            self._skip_depth += 1

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() in self._SKIP_TAGS and self._skip_depth > 0:
            self._skip_depth -= 1

    def handle_data(self, data: str) -> None:
        if self._skip_depth == 0:
            text = data.strip()
            if text:
                self.texts.append(text)


def _extract_jsonld(html: str) -> str | None:
    """
    Find all <script type="application/ld+json"> blocks and return their
    pretty-printed contents joined together, or None if none are present.

    LinkedIn's SEO markup often includes Person schema with name, job title,
    and employer — this is higher-signal than the surrounding HTML noise.
    """
    matches = re.findall(
        r'<script[^>]+type=["\']application/ld\+json["\'][^>]*>(.*?)</script>',
        html,
        re.DOTALL | re.IGNORECASE,
    )
    parts: list[str] = []
    for raw in matches:
        try:
            data = json.loads(raw.strip())
            parts.append(json.dumps(data, indent=2))
        except json.JSONDecodeError:
            continue
    return "\n\n".join(parts) if parts else None


def fetch_linkedin_profile_text(url: str) -> str:
    """
    Fetch a LinkedIn public profile and return extracted plain text.

    Combines JSON-LD structured data (if present) with visible page text.
    The JSON-LD block is placed first so the Ollama extractor sees the
    cleanest signal before the noisier HTML text.

    Parameters
    ----------
    url:
        A public LinkedIn profile URL (must contain ``linkedin.com/in/``).

    Returns
    -------
    str
        Combined text suitable for passing to ``extractor.extract_profile()``.

    Raises
    ------
    ValueError
        With a user-friendly message on any fetch failure, HTTP error, or
        when the returned content is too short to be a real profile page.
    """
    logger.info("Fetching LinkedIn profile: %s", url)

    try:
        response = requests.get(
            url,
            headers=_HEADERS,
            timeout=_TIMEOUT_SECONDS,
            allow_redirects=True,
        )
    except requests.exceptions.Timeout:
        raise ValueError(
            f"Request timed out after {_TIMEOUT_SECONDS}s. "
            "LinkedIn may be slow or blocking the request."
        )
    except requests.exceptions.RequestException as exc:
        raise ValueError(f"Failed to fetch LinkedIn profile: {exc}")

    # LinkedIn returns 999 for bot-detected requests; 401/403 for private profiles.
    if response.status_code in (401, 403, 999):
        raise ValueError(
            "LinkedIn blocked the request. The profile may be private or require "
            "authentication. Please ensure your LinkedIn profile is set to Public."
        )
    if response.status_code != 200:
        raise ValueError(
            f"LinkedIn returned HTTP {response.status_code}. "
            "Check that the URL is correct and the profile is publicly visible."
        )

    html = response.text

    # Extract JSON-LD structured data first — highest signal
    jsonld_text = _extract_jsonld(html)

    # Extract visible page text via the custom parser
    extractor_parser = _HTMLTextExtractor()
    extractor_parser.feed(html)
    visible_text = " ".join(extractor_parser.texts)

    # Combine: structured data leads, raw text follows
    parts: list[str] = []
    if jsonld_text:
        parts.append(f"[Structured Profile Data]\n{jsonld_text}")
    if visible_text:
        parts.append(f"[Page Text]\n{visible_text}")

    combined = "\n\n".join(parts).strip()

    if len(combined) < 100:
        raise ValueError(
            "LinkedIn profile returned very little content. "
            "The profile is likely private or behind a login wall. "
            "Please make your LinkedIn profile public before importing."
        )

    logger.info(
        "LinkedIn profile fetched successfully: %d characters extracted.", len(combined)
    )
    return combined
