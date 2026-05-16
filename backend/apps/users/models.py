from __future__ import annotations

# apps/users/models.py

import uuid

from django.db import models


class UserProfile(models.Model):
    """
    Mirror of the `profiles` table in Supabase.

    `managed = False` means Django will never CREATE, ALTER, or DROP this table.
    Supabase owns the DDL; we only read/write rows through the ORM.

    The primary key `id` is the UUID from Supabase auth.users (`auth.uid()`),
    so joining across auth + profile data is trivial in SQL.
    """

    ROLE_CHOICES = [
        ("hr", "HR"),
        ("employee", "Employee"),
    ]

    PROFILE_STATUS_CHOICES = [
        ("incomplete", "Incomplete"),
        ("submitted", "Submitted"),
        ("approved", "Approved"),
        ("rejected", "Rejected"),
    ]

    # Required by DRF's IsAuthenticated permission check when this model
    # is returned as request.user from the custom authentication class.
    is_authenticated = True

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(unique=True)
    full_name = models.CharField(max_length=255)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES)
    is_active = models.BooleanField(default=True)
    created_by = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="created_users",
        db_column="created_by",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # Phase 2 additional fields (columns added to profiles table in Supabase)
    phone = models.CharField(max_length=20, null=True, blank=True)
    designation = models.CharField(max_length=255, null=True, blank=True)
    department = models.CharField(max_length=255, null=True, blank=True)
    experience_years = models.DecimalField(
        max_digits=4, decimal_places=1, null=True, blank=True
    )
    location = models.CharField(max_length=255, null=True, blank=True)
    avatar_url = models.TextField(null=True, blank=True)
    must_change_password = models.BooleanField(default=True)
    profile_status = models.CharField(
        max_length=20, choices=PROFILE_STATUS_CHOICES, default="incomplete"
    )

    class Meta:
        db_table = "profiles"
        managed = False  # Supabase owns the table DDL

    def __str__(self) -> str:
        return f"{self.email} ({self.role})"
