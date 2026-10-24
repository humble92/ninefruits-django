"""Business audit (original AuditLogger): who did what, to which record, and why. The request
context (request id, IP address, user agent, user) is attached automatically.

    from ninefruits.audit.logger import audit
    audit("student_record.status_changed", subject=record, reason=reason, properties={...})

Implemented by the audit work of Phase 0 (writes ``audit.activity_log``)."""

from __future__ import annotations

from typing import Any


def audit(
    event: str,
    subject: Any = None,
    *,
    reason: str | None = None,
    properties: dict[str, Any] | None = None,
    causer: Any = None,
    log: str = "default",
) -> Any:
    raise NotImplementedError
