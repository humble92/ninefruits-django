"""Applies the two-factor authentication policy from ``SecuritySettings`` to a user (original
``MfaPolicy``). Settings are read on every call, so a policy change applies on the next
request."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import TYPE_CHECKING

from allauth.mfa.models import Authenticator
from django.utils import timezone

from ninefruits.security.enums import MfaEnforcement, MfaMethod, MfaRequirement

if TYPE_CHECKING:
    from ninefruits.security.models import User
    from ninefruits.settings.groups.security import SecuritySettings


class MfaPolicy:
    def __init__(self, settings: SecuritySettings | None = None) -> None:
        if settings is None:
            from ninefruits.settings.groups.security import SecuritySettings

            settings = SecuritySettings.load()
        self.settings = settings

    def requirement_for(self, user: User) -> MfaRequirement:
        match self.settings.mfa_enforcement:
            case MfaEnforcement.DISABLED:
                return MfaRequirement.NONE
            case MfaEnforcement.RECOMMENDED:
                return MfaRequirement.RECOMMENDED
            case MfaEnforcement.REQUIRED_FOR_ALL:
                return MfaRequirement.REQUIRED
            case MfaEnforcement.REQUIRED_FOR_ROLES:
                return MfaRequirement.REQUIRED if self._holds_required_role(user) else MfaRequirement.RECOMMENDED

    def is_enrolled(self, user: User) -> bool:
        return self.methods_for(user) != []

    def methods_for(self, user: User) -> list[MfaMethod]:
        """Two-factor methods the user can sign in with. Email codes count only while the
        institution allows them."""
        methods: list[MfaMethod] = []
        if uses_authenticator_app(user):
            methods.append(MfaMethod.AUTHENTICATOR_APP)
        if user.email_mfa_enabled_at is not None and self.email_codes_allowed():
            methods.append(MfaMethod.EMAIL_CODE)
        return methods

    def email_codes_allowed(self) -> bool:
        return self.settings.mfa_email_code_enabled

    def must_enroll_now(self, user: User) -> bool:
        """Whether the user must enroll before doing anything else. Starts the grace period the
        first time enforcement applies to the user."""
        if self.requirement_for(user) != MfaRequirement.REQUIRED or self.is_enrolled(user):
            return False
        ends_at = self.grace_ends_at(user)
        return ends_at is None or ends_at <= timezone.now()

    def grace_ends_at(self, user: User) -> datetime | None:
        if self.settings.mfa_grace_period_days <= 0:
            return None
        if user.mfa_grace_started_at is None:
            user.mfa_grace_started_at = timezone.now().replace(microsecond=0)
            user.__class__._default_manager.filter(pk=user.pk).update(mfa_grace_started_at=user.mfa_grace_started_at)
        return user.mfa_grace_started_at + timedelta(days=self.settings.mfa_grace_period_days)

    def remember_device_days(self) -> int:
        return max(0, self.settings.mfa_remember_device_days)

    def _holds_required_role(self, user: User) -> bool:
        if not self.settings.mfa_required_role_ids:
            return False
        from ninefruits.security.models import RoleAssignment

        return (
            RoleAssignment.objects.active()
            .filter(user_id=user.pk, role_id__in=self.settings.mfa_required_role_ids)
            .exists()
        )


def uses_authenticator_app(user: User) -> bool:
    """A confirmed authenticator app (allauth TOTP authenticator, ADR 0001-django)."""
    return bool(Authenticator.objects.filter(user_id=user.pk, type=Authenticator.Type.TOTP).exists())
