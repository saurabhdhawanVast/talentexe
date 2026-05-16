from __future__ import annotations

# apps/profiles/urls.py

from django.urls import path

from .views import (
    DownloadProfileView,
    ProfileCertificationDetailView,
    ProfileCertificationsView,
    ProfileDetailView,
    ProfileEducationDetailView,
    ProfileEducationView,
    ProfileExperienceDetailView,
    ProfileExperiencesView,
    ProfileProjectDetailView,
    ProfileProjectsView,
    ProfileSkillDetailView,
    ProfileSkillsView,
    ResumeUploadView,
    SubmitReviewView,
)

urlpatterns = [
    # ---- Core profile ----
    path("<uuid:pk>/", ProfileDetailView.as_view(), name="profile-detail"),
    path("<uuid:pk>/resume/", ResumeUploadView.as_view(), name="profile-resume"),
    path(
        "<uuid:pk>/submit-review/",
        SubmitReviewView.as_view(),
        name="profile-submit-review",
    ),
    path(
        "<uuid:pk>/download/",
        DownloadProfileView.as_view(),
        name="profile-download",
    ),
    # ---- Skills ----
    path("<uuid:pk>/skills/", ProfileSkillsView.as_view(), name="profile-skills"),
    path(
        "<uuid:pk>/skills/<uuid:sk>/",
        ProfileSkillDetailView.as_view(),
        name="profile-skill-detail",
    ),
    # ---- Experiences ----
    path(
        "<uuid:pk>/experiences/",
        ProfileExperiencesView.as_view(),
        name="profile-experiences",
    ),
    path(
        "<uuid:pk>/experiences/<uuid:ek>/",
        ProfileExperienceDetailView.as_view(),
        name="profile-experience-detail",
    ),
    # ---- Projects ----
    path(
        "<uuid:pk>/projects/",
        ProfileProjectsView.as_view(),
        name="profile-projects",
    ),
    path(
        "<uuid:pk>/projects/<uuid:proj_pk>/",
        ProfileProjectDetailView.as_view(),
        name="profile-project-detail",
    ),
    # ---- Certifications ----
    path(
        "<uuid:pk>/certifications/",
        ProfileCertificationsView.as_view(),
        name="profile-certifications",
    ),
    path(
        "<uuid:pk>/certifications/<uuid:ck>/",
        ProfileCertificationDetailView.as_view(),
        name="profile-certification-detail",
    ),
    # ---- Education ----
    path(
        "<uuid:pk>/education/",
        ProfileEducationView.as_view(),
        name="profile-education",
    ),
    path(
        "<uuid:pk>/education/<uuid:ek>/",
        ProfileEducationDetailView.as_view(),
        name="profile-education-detail",
    ),
]
