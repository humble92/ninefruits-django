"""Two-factor challenge routes, mounted under ``/accounts/`` before allauth's own routes.

Two-factor enrollment happens only on the portal security page (ADR 0001), so allauth's MFA
management pages redirect there."""

from __future__ import annotations

from django.urls import path
from django.views.generic import RedirectView

from . import views

app_name = "security"

_to_security_page = RedirectView.as_view(pattern_name="portal:security", permanent=False)

urlpatterns = [
    path("2fa/challenge/", views.TwoFactorChallengeView.as_view(), name="two_factor_challenge"),
    path("2fa/challenge/email/", views.TwoFactorEmailChallengeView.as_view(), name="two_factor_email"),
    path("2fa/challenge/email/send/", views.TwoFactorEmailSendView.as_view(), name="two_factor_email_send"),
    # allauth MFA management pages -> portal security page.
    path("2fa/", _to_security_page),
    path("2fa/totp/activate/", _to_security_page),
    path("2fa/totp/deactivate/", _to_security_page),
    path("2fa/recovery-codes/", _to_security_page),
    path("2fa/recovery-codes/generate/", _to_security_page),
    path("2fa/recovery-codes/download/", _to_security_page),
    # Password changes go through UpdateUserPassword (other sessions end, security event);
    # the sign-in email is changed by staff (UpdateUserAccount), not by adding addresses.
    path("password/change/", _to_security_page),
    path("email/", _to_security_page),
    path("2fa/authenticate/", RedirectView.as_view(pattern_name="security:two_factor_challenge")),
]
