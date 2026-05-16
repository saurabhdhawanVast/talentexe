from __future__ import annotations

# apps/dashboard/views.py

import logging

from django.db import models
from django.db.models import Count, F

from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.users.authentication import SupabaseJWTAuthentication
from apps.users.models import UserProfile
from apps.users.permissions import IsHR

logger = logging.getLogger(__name__)

_AUTH = [SupabaseJWTAuthentication]


def _ok(data: object, http_status: int = 200) -> Response:
    return Response({"data": data, "error": None, "meta": {}}, status=http_status)


def _err(message: str, detail: str = "", http_status: int = 400) -> Response:
    return Response(
        {"data": None, "error": message, "meta": {"detail": detail}},
        status=http_status,
    )


class DashboardStatsView(APIView):
    """
    GET /api/v1/dashboard/stats/

    HR only. Returns aggregate statistics for the HR dashboard:
    - total_employees
    - pending_reviews
    - incomplete_profiles
    - approved_profiles
    - bench_employees (approximated as approved_profiles until project allocation exists)
    - top_skills (top 5 most common skills across approved employees only)
    """

    authentication_classes = _AUTH
    permission_classes = [IsAuthenticated, IsHR]

    def get(self, request: Request) -> Response:
        # Import here to avoid circular imports at module load time
        from apps.profiles.models import EmployeeSkill  # noqa: PLC0415
        from apps.reviews.models import ProfileReview  # noqa: PLC0415

        total_employees: int = UserProfile.objects.filter(role="employee").count()
        pending_reviews: int = ProfileReview.objects.filter(status="pending").count()
        incomplete_profiles: int = UserProfile.objects.filter(
            role="employee", profile_status="incomplete"
        ).count()
        approved_profiles: int = UserProfile.objects.filter(
            role="employee", profile_status="approved"
        ).count()
        # bench = approved employees with no active project (no project table yet)
        bench_employees: int = approved_profiles

        # Aggregate skill counts from the normalised employee_skills table
        top_skills: list[dict] = []
        try:
            top_skills = list(
                EmployeeSkill.objects
                .filter(profile__profile_status="approved")
                .values(name=F("skill__name"))
                .annotate(count=Count("id"))
                .order_by("-count")[:5]
            )
        except Exception as exc:
            logger.warning("Skill aggregation failed: %s", exc)

        return _ok(
            {
                "total_employees": total_employees,
                "pending_reviews": pending_reviews,
                "incomplete_profiles": incomplete_profiles,
                "approved_profiles": approved_profiles,
                "bench_employees": bench_employees,
                "top_skills": top_skills,
            }
        )
