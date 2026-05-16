from __future__ import annotations

import re

from django import forms
from django.contrib import admin, messages
from django.core.validators import URLValidator
from django.http import HttpRequest, HttpResponseRedirect

from .models import UserProfile

_EMPLOYEE_FIELDS = ("designation", "department", "experience_years", "location", "avatar_url")

_PHONE_RE = re.compile(r"^[\d\s\+\-\(\)\.]{6,20}$")


class UserProfileAdminForm(forms.ModelForm):
    class Meta:
        model = UserProfile
        fields = "__all__"

    # ------------------------------------------------------------------
    # Field-level validators
    # ------------------------------------------------------------------

    def clean_full_name(self):
        value = (self.cleaned_data.get("full_name") or "").strip()
        if not value:
            raise forms.ValidationError("Full name is required.")
        if len(value) < 2:
            raise forms.ValidationError("Full name must be at least 2 characters.")
        if len(value) > 255:
            raise forms.ValidationError("Full name must be 255 characters or fewer.")
        return value

    def clean_email(self):
        email = (self.cleaned_data.get("email") or "").strip().lower()
        if not email:
            raise forms.ValidationError("Email address is required.")
        qs = UserProfile.objects.filter(email__iexact=email)
        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise forms.ValidationError("A user with this email already exists.")
        return email

    def clean_role(self):
        value = self.cleaned_data.get("role")
        valid = {c[0] for c in UserProfile.ROLE_CHOICES}
        if not value or value not in valid:
            raise forms.ValidationError("Select a valid role.")
        return value

    def clean_phone(self):
        value = (self.cleaned_data.get("phone") or "").strip()
        if not value:
            return None
        if not _PHONE_RE.match(value):
            raise forms.ValidationError(
                "Enter a valid phone number (digits, spaces, +, -, parentheses; 6–20 characters)."
            )
        return value

    def clean_designation(self):
        value = (self.cleaned_data.get("designation") or "").strip()
        if len(value) > 255:
            raise forms.ValidationError("Designation must be 255 characters or fewer.")
        return value or None

    def clean_department(self):
        value = (self.cleaned_data.get("department") or "").strip()
        if len(value) > 255:
            raise forms.ValidationError("Department must be 255 characters or fewer.")
        return value or None

    def clean_experience_years(self):
        value = self.cleaned_data.get("experience_years")
        if value is None:
            return None
        if value < 0:
            raise forms.ValidationError("Experience years cannot be negative.")
        if value > 60:
            raise forms.ValidationError("Experience years must be 60 or fewer.")
        return value

    def clean_location(self):
        value = (self.cleaned_data.get("location") or "").strip()
        if len(value) > 255:
            raise forms.ValidationError("Location must be 255 characters or fewer.")
        return value or None

    def clean_avatar_url(self):
        value = (self.cleaned_data.get("avatar_url") or "").strip()
        if not value:
            return None
        validate = URLValidator(schemes=["http", "https"])
        try:
            validate(value)
        except forms.ValidationError:
            raise forms.ValidationError("Enter a valid URL starting with http:// or https://.")
        return value

    # ------------------------------------------------------------------
    # Cross-field validation
    # ------------------------------------------------------------------

    def clean(self):
        cleaned_data = super().clean()
        role = cleaned_data.get("role")
        if role == "employee":
            if not (cleaned_data.get("designation") or "").strip():
                self.add_error("designation", "Designation is required for employees.")
            if not (cleaned_data.get("department") or "").strip():
                self.add_error("department", "Department is required for employees.")
        return cleaned_data


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    form = UserProfileAdminForm
    list_display = ("email", "full_name", "role", "is_active", "created_at")
    list_filter = ("role", "is_active")
    search_fields = ("email", "full_name")
    readonly_fields = ("id", "created_at", "updated_at")

    class Media:
        js = ("admin/js/user_profile_role.js",)

    def get_fieldsets(self, request, obj=None):
        base = (
            None,
            {
                "fields": (
                    "id", "email", "full_name", "role", "phone",
                    "is_active", "must_change_password", "profile_status",
                    "created_by", "created_at", "updated_at",
                ),
            },
        )
        employee_section = (
            "Employee Details",
            {
                "fields": _EMPLOYEE_FIELDS,
                "classes": ("employee-only-section",),
            },
        )
        # Add view: show employee section (JS will hide it if HR is selected)
        # Change view: only show employee section when the saved role is employee
        if obj is None or obj.role == "employee":
            return [base, employee_section]
        return [base]

    def save_model(self, request: HttpRequest, obj: UserProfile, form, change: bool) -> None:
        if not change:
            from .services import create_supabase_user, get_supabase_user_by_email

            existing = get_supabase_user_by_email(obj.email)
            if existing:
                request._admin_save_error = (
                    f"This email is already registered in Supabase Auth "
                    f"(user id: {existing.id}). "
                    "Delete the user from Supabase Authentication first, then try again."
                )
                return

            try:
                supabase_id, temp_password = create_supabase_user(obj.email, obj.full_name, obj.role)
                obj.id = supabase_id
            except Exception as exc:
                request._admin_save_error = f"Supabase error: {exc}"
                return

            from .services import delete_supabase_user, send_welcome_email
            try:
                send_welcome_email(obj.email, obj.full_name, temp_password, obj.role)
            except Exception as exc:
                try:
                    delete_supabase_user(str(supabase_id))
                except Exception:
                    pass
                request._admin_save_error = (
                    f"User not created — welcome email failed: {exc}. "
                    "Check your email configuration (BREVO_SMTP_PASSWORD in .env)."
                )
                return

            super().save_model(request, obj, form, change)
            return

        else:
            from .services import update_supabase_user
            try:
                update_supabase_user(str(obj.id), ban=not obj.is_active)
            except Exception as exc:
                self.message_user(request, f"Profile saved, but Supabase sync failed: {exc}", messages.WARNING)

        super().save_model(request, obj, form, change)

    def response_add(self, request, obj, post_url_continue=None):
        if hasattr(request, "_admin_save_error"):
            self.message_user(request, request._admin_save_error, messages.ERROR)
            return HttpResponseRedirect(request.path)
        return super().response_add(request, obj, post_url_continue)

    def delete_model(self, request: HttpRequest, obj: UserProfile) -> None:
        from .services import delete_supabase_user
        try:
            delete_supabase_user(str(obj.id))
        except Exception as exc:
            self.message_user(request, f"Supabase deletion failed: {exc}", messages.WARNING)
        super().delete_model(request, obj)

    def delete_queryset(self, request: HttpRequest, queryset) -> None:
        from .services import delete_supabase_user
        for obj in queryset:
            try:
                delete_supabase_user(str(obj.id))
            except Exception as exc:
                self.message_user(request, f"Could not delete {obj.email} from Supabase: {exc}", messages.WARNING)
        super().delete_queryset(request, queryset)
