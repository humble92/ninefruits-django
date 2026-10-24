"""django-allauth adapters (porting-plan 7.1, original ``FortifyServiceProvider``).

- Sign-in: ``LoginIdentifierBackend`` checks the password (email or student number, lockout,
  same failure for every reason); the login rate limit is keyed by account and IP so email and
  student number share one limit.
- Two-factor step: ``TwoFactorChallengeStage`` replaces allauth's MFA authenticate and trust
  stages (email codes, remembered devices bound to the enrollment).
- Self sign-up is for applicants only and only while ``admissions.applicant_registration_enabled``
  is on; the admission settings group and ``RegisterApplicant`` arrive in Phase 3, so sign-up is
  closed until then.
- SSO never creates accounts (accounts belong to people); the OIDC sign-in flow and linking rules
  are Phase 2 (``ninefruits.security.services.sso``)."""

from __future__ import annotations

from typing import Any

from allauth.account.adapter import DefaultAccountAdapter
from allauth.mfa.adapter import DefaultMFAAdapter
from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from django.conf import settings
from django.http import HttpRequest
from django.utils.translation import gettext_lazy as _

from ninefruits.security.crypto import decrypt_string, encrypt_string

TWO_FACTOR_STAGE = "ninefruits.security.stages.TwoFactorChallengeStage"


def applicant_registration_enabled() -> bool:
    """``AdmissionSettings.applicant_registration_enabled`` (original default: on). Closed while
    the admission settings group does not exist yet (Phase 3)."""
    from ninefruits.settings.groups.base import MissingSettings, SettingsGroup

    group = SettingsGroup.registry.get("admissions")
    if group is None:
        return False
    try:
        return bool(getattr(group.load(), "applicant_registration_enabled", False))
    except MissingSettings:
        return False


class AccountAdapter(DefaultAccountAdapter):
    error_messages = {
        **DefaultAccountAdapter.error_messages,
        # One message for every failure, so it reveals nothing about the account.
        "email_password_mismatch": _("These credentials do not match our records."),
        "username_password_mismatch": _("These credentials do not match our records."),
        "too_many_login_attempts": _("Too many login attempts. Please try again later."),
    }

    def is_open_for_signup(self, request: HttpRequest) -> bool:
        return applicant_registration_enabled()

    def get_login_stages(self) -> list[str]:
        stages = [
            stage
            for stage in super().get_login_stages()
            if stage not in ("allauth.mfa.stages.AuthenticateStage", "allauth.mfa.stages.TrustStage")
        ]
        return [*stages, TWO_FACTOR_STAGE]

    def _get_login_attempts_cache_key(self, request: HttpRequest, **credentials: Any) -> str:
        """Keyed by account when the sign-in name resolves to one, plus the IP address."""
        from ninefruits.security.services.login_identifier import LoginIdentifierResolver

        identifier = str(credentials.get("login") or credentials.get("email") or "")
        account = LoginIdentifierResolver().resolve(identifier)
        key = f"user:{account.pk}" if account is not None else identifier.strip().lower()
        return f"{key}|{self.get_client_ip(request)}"

    def get_client_ip(self, request: HttpRequest) -> str:
        return str(request.META.get("REMOTE_ADDR") or "")


class SocialAccountAdapter(DefaultSocialAccountAdapter):
    def is_open_for_signup(self, request: HttpRequest, sociallogin: Any) -> bool:
        """SSO sign-in never creates an account (ADR 0007)."""
        return False


class MfaAdapter(DefaultMFAAdapter):
    def encrypt(self, text: str) -> str:
        return encrypt_string(text)

    def decrypt(self, encrypted_text: str) -> str:
        return decrypt_string(encrypted_text)

    def get_totp_issuer(self) -> str:
        return str(settings.APP_NAME)
