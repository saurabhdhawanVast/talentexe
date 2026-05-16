from __future__ import annotations

# apps/ai_integration/views.py

import uuid

from django.conf import settings

"""
AI extraction views.

POST /api/v1/ai/extract/{resume_upload_id}/
    Trigger resume extraction for a specific upload.

GET  /api/v1/ai/extractions/{profile_id}/
    Return the latest AIProfileExtraction for a profile.
"""

import logging

from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.profiles.models import AIProfileExtraction, EmployeeEmbedding, ResumeUpload
from apps.users.authentication import SupabaseJWTAuthentication
from apps.users.models import UserProfile

from .pipeline import run_extraction

logger = logging.getLogger(__name__)

_AUTH = [SupabaseJWTAuthentication]


# ---------------------------------------------------------------------------
# Response helpers (mirrors the pattern used throughout the codebase)
# ---------------------------------------------------------------------------


def _ok(data: object, meta: dict | None = None, http_status: int = 200) -> Response:
    return Response(
        {"data": data, "error": None, "meta": meta or {}}, status=http_status
    )


def _err(message: str, detail: str = "", http_status: int = 400) -> Response:
    return Response(
        {"data": None, "error": message, "meta": {"detail": detail}},
        status=http_status,
    )


# ---------------------------------------------------------------------------
# Access-control helper
# ---------------------------------------------------------------------------


def _can_access(request: Request, profile: UserProfile) -> bool:
    """HR can access any profile; employees only their own."""
    if request.user.role == "hr":
        return True
    return str(request.user.id) == str(profile.id)


# ---------------------------------------------------------------------------
# Views
# ---------------------------------------------------------------------------


class ExtractionTriggerView(APIView):
    """
    POST /api/v1/ai/extract/{resume_upload_id}/

    Trigger AI extraction for a resume upload. Runs synchronously and returns
    once extraction is complete (or failed).

    Access: HR can trigger extraction for any profile; employees can only
    trigger extraction for their own uploads.

    Returns
    -------
    200 — extraction already completed previously (returns existing result)
    201 — extraction just completed successfully
    403 — caller does not own the resume and is not HR
    404 — resume upload not found
    500 — extraction failed (Ollama error, bad file, etc.)
    """

    authentication_classes = _AUTH
    permission_classes = [IsAuthenticated]

    def post(self, request: Request, resume_upload_id: str) -> Response:
        # Resolve the ResumeUpload
        try:
            upload = ResumeUpload.objects.select_related("profile").get(
                id=str(resume_upload_id)
            )
        except ResumeUpload.DoesNotExist:
            return _err("Resume upload not found.", http_status=404)

        profile: UserProfile = upload.profile

        # Access control
        if not _can_access(request, profile):
            return _err(
                "Permission denied.",
                detail="You can only trigger extraction for your own resumes.",
                http_status=403,
            )

        # If already completed, return the existing extraction result
        if upload.extraction_status == "completed":
            existing = (
                AIProfileExtraction.objects.filter(
                    resume_upload=upload, status="completed"
                )
                .order_by("-created_at")
                .first()
            )
            data: dict = {
                "extraction_id": str(existing.id) if existing else None,
                "status": "completed",
                "profile_id": str(profile.id),
                "already_completed": True,
            }
            return _ok(data, meta={"message": "Extraction already completed."})

        # Run extraction synchronously
        try:
            result = run_extraction(str(resume_upload_id))
        except ResumeUpload.DoesNotExist:
            return _err("Resume upload not found.", http_status=404)
        except ValueError as exc:
            logger.error(
                "Extraction ValueError for upload=%s: %s", resume_upload_id, exc
            )
            return _err(
                "Extraction failed.",
                detail=str(exc),
                http_status=500,
            )
        except Exception as exc:
            logger.exception(
                "Unexpected extraction error for upload=%s: %s", resume_upload_id, exc
            )
            return _err(
                "An unexpected error occurred during extraction.",
                detail=str(exc),
                http_status=500,
            )

        return _ok(
            {
                "extraction_id": result["extraction_id"],
                "status": result["status"],
                "profile_id": str(profile.id),
                "already_completed": False,
            },
            http_status=201,
        )


class ExtractionStatusView(APIView):
    """
    GET /api/v1/ai/extractions/{profile_id}/

    Return the most recent AIProfileExtraction for a profile, including
    the extracted JSON payload and current status.

    Access: HR can query any profile; employees only their own.

    Returns
    -------
    200 — extraction record found
    403 — permission denied
    404 — profile or extraction not found
    """

    authentication_classes = _AUTH
    permission_classes = [IsAuthenticated]

    def get(self, request: Request, profile_id: str) -> Response:
        # Resolve the UserProfile
        try:
            profile = UserProfile.objects.get(id=str(profile_id), is_active=True)
        except UserProfile.DoesNotExist:
            return _err("Profile not found.", http_status=404)

        # Access control
        if not _can_access(request, profile):
            return _err("Permission denied.", http_status=403)

        # Fetch the latest extraction record
        extraction = (
            AIProfileExtraction.objects.filter(profile=profile)
            .order_by("-created_at")
            .first()
        )
        if not extraction:
            return _err(
                "No extraction record found for this profile.",
                detail="Trigger extraction first via POST /api/v1/ai/extract/{resume_upload_id}/",
                http_status=404,
            )

        data = {
            "extraction_id": str(extraction.id),
            "profile_id": str(profile.id),
            "status": extraction.status,
            "model_name": extraction.model_name,
            "extraction_confidence": (
                float(extraction.extraction_confidence)
                if extraction.extraction_confidence is not None
                else None
            ),
            "extracted_json": extraction.extracted_json,
            "created_at": (
                extraction.created_at.isoformat() if extraction.created_at else None
            ),
            "resume_upload_id": (
                str(extraction.resume_upload_id)
                if extraction.resume_upload_id
                else None
            ),
        }
        return _ok(data)


# ---------------------------------------------------------------------------
# LinkedIn extraction
# ---------------------------------------------------------------------------


class LinkedinExtractionView(APIView):
    """
    POST /api/v1/ai/extract-linkedin/

    Body: { "linkedin_url": "https://www.linkedin.com/in/username" }

    Fetches the public LinkedIn profile page, runs Ollama extraction on the
    visible text, populates the employee's normalized profile tables, and
    persists the LinkedIn URL on EmployeeProfile.

    Returns
    -------
    201 — extraction completed successfully
    400 — invalid URL, private/blocked profile, or Ollama extraction error
    500 — unexpected server error
    """

    authentication_classes = _AUTH
    permission_classes = [IsAuthenticated]

    def post(self, request: Request) -> Response:
        linkedin_url = (request.data.get("linkedin_url") or "").strip()
        if not linkedin_url:
            return _err("linkedin_url is required.", http_status=400)
        if "linkedin.com/in/" not in linkedin_url:
            return _err(
                "Invalid LinkedIn URL.",
                detail=(
                    "URL must be a LinkedIn profile URL "
                    "(e.g. https://www.linkedin.com/in/yourprofile)."
                ),
                http_status=400,
            )

        profile: UserProfile = request.user  # SupabaseJWTAuthentication sets request.user to UserProfile

        extraction = None
        try:
            # 1. Fetch and extract text from the public LinkedIn page
            from . import linkedin_scraper
            profile_text = linkedin_scraper.fetch_linkedin_profile_text(linkedin_url)

            # 2. Create an AIProfileExtraction record (resume_upload=None for LinkedIn imports)
            extraction = AIProfileExtraction.objects.create(
                id=uuid.uuid4(),
                profile=profile,
                resume_upload=None,
                status="processing",
                model_name=getattr(settings, "OLLAMA_LLM_MODEL", "llama3.2:3b"),
            )

            # 3. Run Ollama extraction on the fetched text
            from . import extractor as _extractor
            extracted_data = _extractor.extract_profile(profile_text)

            # 4. Persist raw text and extracted JSON to the extraction record
            extraction.raw_text = profile_text
            extraction.extracted_json = extracted_data
            extraction.save(update_fields=["raw_text", "extracted_json"])

            # 5. Write to normalized profile tables (skills, experiences, projects, etc.)
            from .pipeline import populate_profile
            populate_profile(profile, extracted_data)

            # 6. Mark extraction as completed
            extraction.status = "completed"
            extraction.save(update_fields=["status"])

            # 7. Save the LinkedIn URL to EmployeeProfile
            from apps.profiles.models import EmployeeProfile as EmpProfile
            emp_profile, _ = EmpProfile.objects.get_or_create(
                profile=profile,
                defaults={"id": uuid.uuid4()},
            )
            emp_profile.linkedin_url = linkedin_url
            emp_profile.save(update_fields=["linkedin_url"])

            logger.info(
                "LinkedIn extraction completed: extraction_id=%s profile_id=%s",
                extraction.id,
                profile.id,
            )

        except ValueError as exc:
            logger.error(
                "LinkedIn extraction ValueError for profile=%s: %s", profile.id, exc
            )
            if extraction is not None:
                try:
                    extraction.status = "failed"
                    extraction.save(update_fields=["status"])
                except Exception:
                    pass
            return _err(str(exc), http_status=400)

        except Exception as exc:
            logger.exception(
                "LinkedIn extraction unexpected error for profile=%s: %s", profile.id, exc
            )
            if extraction is not None:
                try:
                    extraction.status = "failed"
                    extraction.save(update_fields=["status"])
                except Exception:
                    pass
            return _err(
                "An unexpected error occurred during LinkedIn extraction.",
                detail=str(exc),
                http_status=500,
            )

        return _ok(
            {
                "extraction_id": str(extraction.id),
                "status": "completed",
                "profile_id": str(profile.id),
            },
            http_status=201,
        )


# ---------------------------------------------------------------------------
# Semantic Search
# ---------------------------------------------------------------------------


class SearchView(APIView):
    """
    POST /api/v1/search/

    Run the NLP semantic search pipeline and return ranked employee results.
    Only approved employee profiles are returned.

    Auth: HR role only.

    Request body:
        { "query": "...", "filters": { "location": null, "min_years": null, "department": null } }

    Response:
        { "data": { "query_parsed": {...}, "results": [...], "total": N } }
    """

    authentication_classes = _AUTH
    permission_classes = [IsAuthenticated]

    def post(self, request: Request) -> Response:
        if request.user.role != "hr":
            return _err("Only HR users can access Smart Search.", http_status=403)

        query = (request.data.get("query") or "").strip()
        if not query:
            return _err("query is required.", http_status=400)

        filters: dict = request.data.get("filters") or {}

        from .searcher import search
        try:
            result = search(query, filters)
        except ValueError as exc:
            return _err(str(exc), http_status=400)
        except Exception as exc:
            logger.exception("Search failed: %s", exc)
            return _err("Search temporarily unavailable.", detail=str(exc), http_status=503)

        return _ok(result)


# ---------------------------------------------------------------------------
# Embedding Generation
# ---------------------------------------------------------------------------


class GenerateEmbeddingView(APIView):
    """
    POST /api/v1/profiles/{profile_id}/generate-embedding/

    Generate (or refresh) the vector embedding for an approved employee profile.

    Auth: HR role only.
    """

    authentication_classes = _AUTH
    permission_classes = [IsAuthenticated]

    def post(self, request: Request, profile_id: str) -> Response:
        if request.user.role != "hr":
            return _err("Only HR users can trigger embedding generation.", http_status=403)

        try:
            profile = UserProfile.objects.get(id=str(profile_id), is_active=True)
        except UserProfile.DoesNotExist:
            return _err("Profile not found.", http_status=404)

        if profile.profile_status != "approved":
            return _err(
                "Embeddings can only be generated for approved profiles.",
                http_status=400,
            )

        from .profile_text_builder import build_searchable_text
        from .embedder import generate_embedding

        try:
            searchable_text = build_searchable_text(profile)
            if not searchable_text.strip():
                return _err("Profile has no content to embed.", http_status=400)

            embedding = generate_embedding(searchable_text)
        except ValueError as exc:
            return _err(str(exc), http_status=503)
        except Exception as exc:
            logger.exception("Embedding generation failed for profile %s: %s", profile_id, exc)
            return _err("Embedding generation failed.", detail=str(exc), http_status=500)

        # Upsert into employee_embeddings via raw SQL (pgvector column)
        from django.db import connection
        embedding_str = "[" + ",".join(str(v) for v in embedding) + "]"
        with connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO employee_embeddings (id, profile_id, embedding_type, embedding, searchable_text, updated_at)
                VALUES (gen_random_uuid(), %s, 'profile', %s::vector, %s, NOW())
                ON CONFLICT (profile_id, embedding_type)
                DO UPDATE SET
                    embedding = EXCLUDED.embedding,
                    searchable_text = EXCLUDED.searchable_text,
                    updated_at = NOW()
                """,
                [str(profile.id), embedding_str, searchable_text],
            )

        logger.info("Embedding generated/refreshed for profile %s (%d dims)", profile_id, len(embedding))
        return _ok({"profile_id": str(profile.id), "dims": len(embedding), "status": "ok"})
