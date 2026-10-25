"""Portal routes of the registration, included in ``ninefruits.portal.urls`` (names
``portal:...``)."""

from __future__ import annotations

from django.urls import path

from ninefruits.registration.views.portal import RegistrationView

urlpatterns = [
    path("registration/", RegistrationView.as_view(), name="registration"),
]
