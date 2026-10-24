"""Business audit (original AuditLogger): who did what, to which record, and why. The request
context (request id, IP address, user agent, user) is attached automatically.

    from ninefruits.audit.logger import audit
    audit("student_record.status_changed", subject=record, reason=reason, properties={...})

Writes ``audit.activity_log`` (log name ``default`` unless given; ``command`` for
AuditedCommand runs). The description is the event, as in the original."""

from __future__ import annotations

import re
from collections.abc import Mapping
from typing import TYPE_CHECKING, Any

from django.conf import settings
from django.utils import timezone

from ninefruits.core import context, morph

if TYPE_CHECKING:
    from ninefruits.audit.models import ActivityLog

REDACTED = "[redacted]"

# Property names whose values never belong in an audit record (same marker as the data audit
# trigger uses for its secret columns). Matched per word of the key: ``new_password``,
# ``api-token``, ``client_secret``.
_SENSITIVE_WORDS = frozenset({"password", "passwd", "secret", "token", "otp", "credential", "credentials"})
_SENSITIVE_PHRASES = ("api_key", "apikey", "private_key", "recovery_code")
_WORD_SEPARATOR = re.compile(r"[_\-\s.]+")


def is_sensitive_key(key: object) -> bool:
    if not isinstance(key, str):
        return False
    lowered = key.lower()
    normalized = _WORD_SEPARATOR.sub("_", lowered)
    return bool(_SENSITIVE_WORDS.intersection(normalized.split("_"))) or any(
        phrase in normalized for phrase in _SENSITIVE_PHRASES
    )


def mask_sensitive(value: Any) -> Any:
    """Replaces values stored under sensitive keys (``password``, ``token``, ``secret`` ...),
    recursively through dicts and lists."""
    if isinstance(value, Mapping):
        return {
            key: REDACTED if is_sensitive_key(key) and item not in (None, "") else mask_sensitive(item)
            for key, item in value.items()
        }
    if isinstance(value, list | tuple):
        return [mask_sensitive(item) for item in value]
    return value


def _user_morph_type() -> str:
    return str(settings.AUTH_USER_MODEL).lower()


def audit(
    event: str,
    subject: Any = None,
    *,
    reason: str | None = None,
    properties: dict[str, Any] | None = None,
    causer: Any = None,
    log: str = "default",
) -> ActivityLog:
    """Records one business audit entry and returns it.

    ``causer`` defaults to the user of the current request context (the signed-in user in a
    request, the initiating user in a Celery task, nobody in a command unless ``--actor``)."""
    from ninefruits.audit.models import ActivityLog

    request = context.current()
    if causer is not None:
        causer_type, causer_id = morph.morph_of(causer)
    elif request.user_id is not None:
        causer_type, causer_id = _user_morph_type(), request.user_id
    else:
        causer_type, causer_id = None, None
    subject_type, subject_id = morph.morph_of(subject)
    now = timezone.now()
    return ActivityLog.objects.create(
        log_name=log,
        description=event,
        event=event,
        subject_type=subject_type,
        subject_id=subject_id,
        causer_type=causer_type,
        causer_id=causer_id,
        properties=mask_sensitive(dict(properties or {})),
        reason=reason,
        request_id=request.request_id,
        ip_address=request.ip_address,
        user_agent=request.user_agent,
        created_at=now,
        updated_at=now,
    )
