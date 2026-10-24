"""Security policy managed by the system administrator (settings group ``security``, original
``App\\Domain\\Security\\Settings\\SecuritySettings``). Read on every request, so changes apply
immediately."""

from __future__ import annotations

from typing import ClassVar

from ninefruits.security.enums import MfaEnforcement
from ninefruits.settings.groups.base import SettingsGroup


class SecuritySettings(SettingsGroup):
    group: ClassVar[str] = "security"

    mfa_enforcement: MfaEnforcement
    #: Roles whose members must use two-factor authentication (``required_for_roles``).
    mfa_required_role_ids: list[int]
    #: Days a user may keep working after enforcement first applies to them.
    mfa_grace_period_days: int
    #: Days a device is remembered after a successful challenge. 0 disables.
    mfa_remember_device_days: int
    #: Whether users may use one-time codes sent by email as their two-factor method.
    #: Turning it off stops email codes from counting as two-factor authentication.
    mfa_email_code_enabled: bool
