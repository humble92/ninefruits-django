"""Person routes outside the admin and the portal (invitation links, photos)."""

from __future__ import annotations

from django.urls import path

from .views.invitations import InvitationView
from .views.photos import PersonPhotoView

app_name = "person"

urlpatterns = [
    path("invitations/<str:token>/", InvitationView.as_view(), name="invitation"),
    path("people/<int:pk>/photo/", PersonPhotoView.as_view(), name="photo"),
]
