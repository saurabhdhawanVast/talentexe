from __future__ import annotations

# apps/ai_integration/text_extractor.py

"""
Plain-text extraction from resume file bytes.

Supported formats
-----------------
- PDF  : pdfminer.six
- DOCX : python-docx
- DOC  : best-effort UTF-8 decode (binary Word format is not parseable
          without antiword/LibreOffice; we extract whatever readable text
          happens to survive a lossy decode rather than failing hard)

All public functions are intentionally non-raising — callers receive an
empty string on any failure so the pipeline can mark the extraction as
failed without an uncaught exception propagating to the view.
"""

import io
import logging

logger = logging.getLogger(__name__)


def _extract_pdf(file_bytes: bytes) -> str:
    """Extract text from PDF bytes using pdfminer.six."""
    try:
        from pdfminer.high_level import extract_text_to_fp
        from pdfminer.layout import LAParams

        output = io.StringIO()
        input_fp = io.BytesIO(file_bytes)
        extract_text_to_fp(input_fp, output, laparams=LAParams(), output_type="text", codec="utf-8")
        return output.getvalue()
    except Exception as exc:
        logger.warning("PDF text extraction failed: %s", exc)
        return ""


def _extract_docx(file_bytes: bytes) -> str:
    """Extract text from DOCX bytes using python-docx."""
    try:
        from docx import Document

        doc = Document(io.BytesIO(file_bytes))
        paragraphs = [para.text for para in doc.paragraphs if para.text.strip()]
        # Also pull text from tables
        for table in doc.tables:
            for row in table.rows:
                for cell in row.cells:
                    cell_text = cell.text.strip()
                    if cell_text:
                        paragraphs.append(cell_text)
        return "\n".join(paragraphs)
    except Exception as exc:
        logger.warning("DOCX text extraction failed: %s", exc)
        return ""


def _extract_doc_fallback(file_bytes: bytes) -> str:
    """
    Best-effort text extraction from legacy .doc (binary Word OLE) files.

    The binary .doc format is not fully parseable without external tools.
    We attempt a lossy UTF-8 decode and strip non-printable bytes, which
    recovers a readable fraction of the text content for most documents.
    """
    try:
        text = file_bytes.decode("utf-8", errors="ignore")
        # Keep only lines that contain at least a few printable characters
        lines = [
            line.strip()
            for line in text.splitlines()
            if len(line.strip()) > 3 and line.strip().isprintable() is False or len(line.strip()) > 3
        ]
        return "\n".join(lines)
    except Exception as exc:
        logger.warning("DOC fallback extraction failed: %s", exc)
        return ""


def extract_text(file_bytes: bytes, mime_type: str) -> str:
    """
    Extract plain text from resume file bytes.

    Parameters
    ----------
    file_bytes:
        Raw bytes of the uploaded file.
    mime_type:
        The MIME type declared at upload time (e.g. ``application/pdf``).

    Returns
    -------
    str
        Extracted plain text, possibly empty if extraction fails or if the
        file contains no machine-readable text (e.g. a scanned image PDF).
        Never raises — callers should treat an empty return as a soft failure.
    """
    if not file_bytes:
        return ""

    mime_type = (mime_type or "").lower().strip()

    if mime_type == "application/pdf":
        return _extract_pdf(file_bytes)

    if mime_type in (
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "application/docx",
    ):
        return _extract_docx(file_bytes)

    if mime_type == "application/msword":
        # Try DOCX parser first (some .doc files are actually DOCX with wrong MIME)
        result = _extract_docx(file_bytes)
        if result.strip():
            return result
        return _extract_doc_fallback(file_bytes)

    # Unknown mime type — attempt DOCX, then PDF, then raw decode
    logger.warning("Unknown mime_type '%s'; attempting heuristic extraction.", mime_type)
    result = _extract_docx(file_bytes)
    if result.strip():
        return result
    result = _extract_pdf(file_bytes)
    if result.strip():
        return result
    return _extract_doc_fallback(file_bytes)
