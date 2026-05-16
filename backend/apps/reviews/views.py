from __future__ import annotations

# apps/reviews/views.py

import logging

from django.utils import timezone
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.users.authentication import SupabaseJWTAuthentication
from apps.users.permissions import IsHR
from apps.users.services import send_approval_email, send_rejection_email
from apps.users.models import UserProfile

from .models import ProfileReview
from .serializers import ProfileReviewSerializer, RejectInputSerializer

logger = logging.getLogger(__name__)

_AUTH = [SupabaseJWTAuthentication]


def _ok(data: object, meta: dict | None = None, http_status: int = 200) -> Response:
    return Response(
        {"data": data, "error": None, "meta": meta or {}}, status=http_status
    )


def _err(message: str, detail: str = "", http_status: int = 400) -> Response:
    return Response(
        {"data": None, "error": message, "meta": {"detail": detail}},
        status=http_status,
    )


class ReviewListView(APIView):
    """
    GET /api/v1/reviews/

    HR only. Returns a paginated list of ProfileReview rows.
    Query params:
        status   — filter by status (default: 'pending')
        page     — default 1
        page_size — default 20
    """

    authentication_classes = _AUTH
    permission_classes = [IsAuthenticated, IsHR]

    def get(self, request: Request) -> Response:
        status_filter = request.query_params.get("status", "pending").strip()
        profile_id = request.query_params.get("profile_id", "").strip()
        qs = ProfileReview.objects.select_related("profile", "reviewed_by").order_by(
            "-submitted_at"
        )
        if status_filter:
            qs = qs.filter(status=status_filter)
        if profile_id:
            qs = qs.filter(profile_id=profile_id)

        try:
            page = max(1, int(request.query_params.get("page", 1)))
            page_size = min(
                100, max(1, int(request.query_params.get("page_size", 20)))
            )
        except ValueError:
            page, page_size = 1, 20

        total = qs.count()
        start = (page - 1) * page_size
        reviews = qs[start : start + page_size]

        serializer = ProfileReviewSerializer(reviews, many=True)
        return _ok(
            serializer.data,
            meta={
                "total": total,
                "page": page,
                "page_size": page_size,
                "pages": (total + page_size - 1) // page_size,
                "status_filter": status_filter,
            },
        )


class ApproveReviewView(APIView):
    """
    POST /api/v1/reviews/{id}/approve/

    HR only. Approves the review: sets review.status='approved',
    sets profile.profile_status='approved', and sends an approval email.
    """

    authentication_classes = _AUTH
    permission_classes = [IsAuthenticated, IsHR]

    def post(self, request: Request, pk: str) -> Response:
        try:
            review = ProfileReview.objects.select_related("profile").get(id=pk)
        except ProfileReview.DoesNotExist:
            return _err("Review not found.", http_status=404)

        if review.status != "pending":
            return _err(
                f"Review has already been {review.status}. Only pending reviews can be approved."
            )

        review.status = "approved"
        review.reviewed_by = request.user
        review.reviewed_at = timezone.now()
        review.save(update_fields=["status", "reviewed_by", "reviewed_at"])

        profile = review.profile
        profile.profile_status = "approved"
        profile.save(update_fields=["profile_status"])

        # Generate and upsert vector embedding so NLP search picks this profile up immediately.
        try:
            from apps.ai_integration.profile_text_builder import build_searchable_text
            from apps.ai_integration.embedder import generate_embedding
            from django.db import connection

            searchable_text = build_searchable_text(profile)
            if searchable_text.strip():
                embedding = generate_embedding(searchable_text)
                embedding_str = "[" + ",".join(str(v) for v in embedding) + "]"
                with connection.cursor() as cursor:
                    cursor.execute(
                        """
                        INSERT INTO employee_embeddings
                            (id, profile_id, embedding_type, embedding, searchable_text, updated_at)
                        VALUES (gen_random_uuid(), %s, 'profile', %s::vector, %s, NOW())
                        ON CONFLICT (profile_id, embedding_type)
                        DO UPDATE SET
                            embedding        = EXCLUDED.embedding,
                            searchable_text  = EXCLUDED.searchable_text,
                            updated_at       = NOW()
                        """,
                        [str(profile.id), embedding_str, searchable_text],
                    )
                logger.info("Embedding generated and stored for profile %s on approval.", profile.id)
        except Exception as exc:
            # Never block approval because of an embedding failure — log and continue.
            logger.warning("Embedding generation failed for profile %s after approval: %s", profile.id, exc)

        send_approval_email(to_email=profile.email, full_name=profile.full_name)

        return _ok(
            {
                "review_id": str(review.id),
                "status": "approved",
                "profile_status": "approved",
            }
        )


class RejectReviewView(APIView):
    """
    POST /api/v1/reviews/{id}/reject/

    HR only. Rejects the review: sets review.status='rejected',
    stores the HR comment, resets profile.profile_status='incomplete',
    and sends a rejection email.

    Body: { "comment": "Please add your certifications." }
    """

    authentication_classes = _AUTH
    permission_classes = [IsAuthenticated, IsHR]

    def post(self, request: Request, pk: str) -> Response:
        try:
            review = ProfileReview.objects.select_related("profile").get(id=pk)
        except ProfileReview.DoesNotExist:
            return _err("Review not found.", http_status=404)

        if review.status != "pending":
            return _err(
                f"Review has already been {review.status}. Only pending reviews can be rejected."
            )

        serializer = RejectInputSerializer(data=request.data)
        if not serializer.is_valid():
            return _err("Validation error.", detail=str(serializer.errors))

        comment: str = serializer.validated_data["comment"]

        review.status = "rejected"
        review.reviewed_by = request.user
        review.reviewed_at = timezone.now()
        review.hr_comment = comment
        review.save(update_fields=["status", "reviewed_by", "reviewed_at", "hr_comment"])

        profile = review.profile
        profile.profile_status = "incomplete"
        profile.save(update_fields=["profile_status"])

        send_rejection_email(
            to_email=profile.email,
            full_name=profile.full_name,
            comment=comment,
        )

        return _ok(
            {
                "review_id": str(review.id),
                "status": "rejected",
                "profile_status": "incomplete",
                "comment": comment,
            }
        )


class MyReviewView(APIView):
    """
    GET /api/v1/reviews/me/

    Employee only. Returns the latest review for the authenticated employee,
    including the hr_comment so the employee can see HR feedback.
    """

    authentication_classes = _AUTH
    permission_classes = [IsAuthenticated]

    def get(self, request: Request) -> Response:
        try:
            review = (
                ProfileReview.objects.select_related("reviewed_by")
                .filter(profile=request.user)
                .order_by("-submitted_at")
                .first()
            )
        except Exception:
            return _err("Failed to fetch review.", http_status=500)

        if not review:
            return _ok(None)

        serializer = ProfileReviewSerializer(review)
        return _ok(serializer.data)
