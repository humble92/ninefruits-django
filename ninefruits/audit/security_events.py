"""Security log (original RecordSecurityEvent): writes ``audit.security_events``.

    from ninefruits.audit.security_events import SecurityEventType, record_security_event
    record_security_event(SecurityEventType.LOGIN_FAILED, identifier=email)

Implemented by the audit work of Phase 0."""

from __future__ import annotations

from enum import StrEnum
from typing import Any


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


def record_security_event(
    type: SecurityEventType,
    *,
    user: Any = None,
    identifier: str | None = None,
    subject: Any = None,
    properties: dict[str, Any] | None = None,
) -> Any:
    raise NotImplementedError
