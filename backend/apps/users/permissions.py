from __future__ import annotations

# apps/users/permissions.py

from rest_framework.permissions import BasePermission
from rest_framework.request import Request
from rest_framework.views import APIView


class IsHR(BasePermission):
    """Allow access only to users with role == 'hr'."""

    def has_permission(self, request: Request, view: APIView) -> bool:
        return bool(
            request.user
            and hasattr(request.user, "role")
            and request.user.role == "hr"
        )


class IsEmployee(BasePermission):
    """Allow access only to users with role == 'employee'."""

    def has_permission(self, request: Request, view: APIView) -> bool:
        return bool(
            request.user
            and hasattr(request.user, "role")
            and request.user.role == "employee"
        )


class IsHROrSelf(BasePermission):
    """
    Allow HR to access any object; allow employees to access only their own.

    The view must set `self.target_profile` before permission is checked,
    or override `get_object` to call `self.check_object_permissions`.
    This class is primarily used as an object-level permission.
    """

    def has_permission(self, request: Request, view: APIView) -> bool:
        return bool(request.user and hasattr(request.user, "role"))

    def has_object_permission(
        self, request: Request, view: APIView, obj: object
    ) -> bool:
        if request.user.role == "hr":
            return True
        # obj is expected to be a UserProfile or have a `profile` FK
        profile_id = getattr(obj, "id", None) or getattr(
            getattr(obj, "profile", None), "id", None
        )
        return str(profile_id) == str(request.user.id)
