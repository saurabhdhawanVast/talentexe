from __future__ import annotations

# apps/reviews/urls.py

from django.urls import path

from .views import ApproveReviewView, MyReviewView, RejectReviewView, ReviewListView

urlpatterns = [
    path("", ReviewListView.as_view(), name="review-list"),
    path("me/", MyReviewView.as_view(), name="review-me"),
    path("<uuid:pk>/approve/", ApproveReviewView.as_view(), name="review-approve"),
    path("<uuid:pk>/reject/", RejectReviewView.as_view(), name="review-reject"),
]
