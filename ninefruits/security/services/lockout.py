"""Locks an account after repeated failed passwords, whatever sign-in name was used (email or
student number), in addition to the per IP rate limit (original ``AccountLockout``). Locked
accounts get the same error as a wrong password, so the message reveals nothing about the
account."""

from __future__ import annotations

from datetime import timedelta
from typing import TYPE_CHECKING

from django.utils import timezone

from ninefruits.audit.security_events import SecurityEventType, record_security_event

if TYPE_CHECKING:
    from ninefruits.security.models import User
    from ninefruits.settings.groups.authentication import AuthenticationSettings


class AccountLockout:
    def __init__(self, settings: AuthenticationSettings | None = None) -> None:
        if settings is None:
            from ninefruits.settings.groups.authentication import AuthenticationSettings

            settings = AuthenticationSettings.load()
        self.settings = settings

    def record_failure(self, user: User) -> None:
        if self.settings.lockout_threshold <= 0:
            return
        count = user.failed_login_count + 1
        values: dict[str, object] = {"failed_login_count": count}
        if count >= self.settings.lockout_threshold:
            values["locked_until"] = timezone.now().replace(microsecond=0) + timedelta(
                minutes=max(1, self.settings.lockout_minutes)
            )
            values["failed_login_count"] = 0
            record_security_event(
                SecurityEventType.LOGIN_LOCKED_OUT,
                user=user,
                identifier=user.email,
                properties={"minutes": self.settings.lockout_minutes},
            )
        user.__class__._default_manager.filter(pk=user.pk).update(**values)
        for name, value in values.items():
            setattr(user, name, value)

    def reset(self, user: User) -> None:
        if user.failed_login_count != 0 or user.locked_until is not None:
            user.__class__._default_manager.filter(pk=user.pk).update(failed_login_count=0, locked_until=None)
            user.failed_login_count = 0
            user.locked_until = None
