"""Security log (original RecordSecurityEvent): writes ``audit.security_events``.

    from ninefruits.audit.security_events import SecurityEventType, record_security_event
    record_security_event(SecurityEventType.LOGIN_FAILED, identifier=email)

The request id, IP address and user agent come from the request context
(``ninefruits.core.context``), which reaches Celery tasks through task headers."""

from __future__ import annotations

from enum import StrEnum
from typing import TYPE_CHECKING, Any

from django.utils.functional import Promise
from django.utils.translation import gettext_lazy as _

from ninefruits.core import context, morph

if TYPE_CHECKING:
    from ninefruits.audit.models import SecurityEvent


class SecurityEventType(StrEnum):
    LOGIN_SUCCEEDED = "login.succeeded"
    LOGIN_FAILED = "login.failed"
    LOGIN_LOCKED_OUT = "login.locked_out"
    ACCOUNT_UNLOCKED = "account.unlocked"
    LOGOUT = "logout"
    PASSWORD_RESET = "password.reset"  # noqa: S105
    MFA_ENABLED = "mfa.enabled"
    MFA_CONFIRMED = "mfa.confirmed"
    MFA_DISABLED = "mfa.disabled"
    MFA_CHALLENGE_FAILED = "mfa.challenge_failed"
    MFA_RECOVERY_CODE_USED = "mfa.recovery_code_used"
    MFA_RECOVERY_CODES_REGENERATED = "mfa.recovery_codes_regenerated"
    MFA_RESET = "mfa.reset"
    MFA_EMAIL_CODE_SENT = "mfa.email_code_sent"
    MFA_EMAIL_ENABLED = "mfa.email_enabled"
    MFA_EMAIL_DISABLED = "mfa.email_disabled"
    ROLE_ASSIGNED = "role.assigned"
    ROLE_ASSIGNMENT_REVOKED = "role.assignment_revoked"
    ROLE_PERMISSIONS_CHANGED = "role.permissions_changed"
    SENSITIVE_DATA_REVEALED = "sensitive_data.revealed"
    DATA_EXPORTED = "data.exported"
    AUDIT_PRUNED = "audit.pruned"
    PASSWORD_CHANGED = "password.changed"  # noqa: S105
    EMAIL_CHANGED = "email.changed"

    @property
    def label(self) -> Promise:
        """Translated name for screens (original ``security.event_types.*``)."""
        return _LABELS[self]


_LABELS: dict[SecurityEventType, Promise] = {
    SecurityEventType.LOGIN_SUCCEEDED: _("Signed in"),
    SecurityEventType.LOGIN_FAILED: _("Sign-in failed"),
    SecurityEventType.LOGIN_LOCKED_OUT: _("Sign-in locked"),
    SecurityEventType.ACCOUNT_UNLOCKED: _("Account unlocked"),
    SecurityEventType.LOGOUT: _("Signed out"),
    SecurityEventType.PASSWORD_RESET: _("Password reset"),
    SecurityEventType.MFA_ENABLED: _("Two-factor enabled"),
    SecurityEventType.MFA_CONFIRMED: _("Two-factor confirmed"),
    SecurityEventType.MFA_DISABLED: _("Two-factor disabled"),
    SecurityEventType.MFA_CHALLENGE_FAILED: _("Two-factor code rejected"),
    SecurityEventType.MFA_RECOVERY_CODE_USED: _("Recovery code used"),
    SecurityEventType.MFA_RECOVERY_CODES_REGENERATED: _("Recovery codes regenerated"),
    SecurityEventType.MFA_RESET: _("Two-factor reset by administrator"),
    SecurityEventType.MFA_EMAIL_CODE_SENT: _("Email code sent"),
    SecurityEventType.MFA_EMAIL_ENABLED: _("Email codes turned on"),
    SecurityEventType.MFA_EMAIL_DISABLED: _("Email codes turned off"),
    SecurityEventType.ROLE_ASSIGNED: _("Role assigned"),
    SecurityEventType.ROLE_ASSIGNMENT_REVOKED: _("Role assignment ended"),
    SecurityEventType.ROLE_PERMISSIONS_CHANGED: _("Role permissions changed"),
    SecurityEventType.SENSITIVE_DATA_REVEALED: _("Sensitive data revealed"),
    SecurityEventType.DATA_EXPORTED: _("Data exported"),
    SecurityEventType.AUDIT_PRUNED: _("Audit records pruned"),
    SecurityEventType.PASSWORD_CHANGED: _("Password changed"),
    SecurityEventType.EMAIL_CHANGED: _("Email changed"),
}


def record_security_event(
    type: SecurityEventType,
    *,
    user: Any = None,
    identifier: str | None = None,
    subject: Any = None,
    properties: dict[str, Any] | None = None,
) -> SecurityEvent:
    """Appends one security event. ``user`` is the account the event is about (or who did it),
    ``identifier`` the sign-in name typed (failed sign-ins have no user), ``subject`` the record
    concerned. Empty ``properties`` are stored as NULL like the original."""
    from ninefruits.audit.models import SecurityEvent

    request = context.current()
    subject_type, subject_id = morph.morph_of(subject)
    return SecurityEvent.objects.create(
        type=SecurityEventType(type).value,
        user_id=getattr(user, "pk", None),
        identifier=identifier[:255] if identifier else identifier,
        subject_type=subject_type,
        subject_id=subject_id,
        properties=properties or None,
        request_id=request.request_id,
        ip_address=request.ip_address,
        user_agent=request.user_agent,
    )
