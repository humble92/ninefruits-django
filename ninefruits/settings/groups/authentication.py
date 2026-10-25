"""Sign-in methods (settings group ``authentication``, original
``App\\Domain\\Security\\Settings\\AuthenticationSettings``, porting-plan 7.1). The personal email
and password always work; the rest is chosen per institution."""

from __future__ import annotations

from typing import Any, ClassVar

from ninefruits.security.enums import SsoLinkMode, StudentNumberLogin
from ninefruits.settings.groups.base import SettingsGroup


class AuthenticationSettings(SettingsGroup):
    group: ClassVar[str] = "authentication"

    student_number_login: StudentNumberLogin
    #: Accounts linked to a school SSO account may still sign in with their password.
    password_login_for_sso_users: bool
    sso_link_mode: SsoLinkMode
    #: OIDC providers: list of {key, label, issuer, client_id, client_secret (encrypted),
    #: scopes, trusts_mfa, is_enabled}.
    sso_providers: list[dict[str, Any]]
    #: Failed sign-ins before the account is locked. 0 disables locking.
    lockout_threshold: int
    lockout_minutes: int
