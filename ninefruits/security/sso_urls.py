"""School sign-in (SSO) routes, mounted at ``/auth/sso/`` (original ``sso.redirect`` and
``sso.callback``). Not namespaced: ``sso_redirect`` and ``sso_callback``."""

from __future__ import annotations

from django.urls import path

from .views_sso import SsoCallbackView, SsoRedirectView

urlpatterns = [
    path("<str:provider>/redirect/", SsoRedirectView.as_view(), name="sso_redirect"),
    path("<str:provider>/callback/", SsoCallbackView.as_view(), name="sso_callback"),
]
