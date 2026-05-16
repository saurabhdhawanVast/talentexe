from __future__ import annotations

# apps/reviews/models.py

import uuid

from django.db import models


class ProfileReview(models.Model):
    """
    Tracks the HR review lifecycle for an employee profile.

    A new row with status='pending' is created each time an employee
    submits their profile. HR approves or rejects, updating this row
    and the parent UserProfile.profile_status accordingly.

    managed=False — Supabase owns the DDL for `profile_reviews`.
    """

    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("approved", "Approved"),
        ("rejected", "Rejected"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    profile = models.ForeignKey(
        "users.UserProfile",
        on_delete=models.CASCADE,
        related_name="reviews",
        db_column="profile_id",
    )
    reviewed_by = models.ForeignKey(
        "users.UserProfile",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="conducted_reviews",
        db_column="reviewed_by",
    )
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default="pending"
    )
    hr_comment = models.TextField(null=True, blank=True)
    submitted_at = models.DateTimeField(auto_now_add=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "profile_reviews"
        managed = False
        ordering = ["-submitted_at"]

    def __str__(self) -> str:
        return f"ProfileReview({self.profile_id}, {self.status})"
