"""Personal data actions."""

from __future__ import annotations

from typing import Any

from django.core.exceptions import PermissionDenied
from django.db import models

from ninefruits.audit.security_events import SecurityEventType, record_security_event
from ninefruits.pii.fields import ENCRYPTED_SUFFIX, encrypted_pii_fields
from ninefruits.security.enums import Permission


class RevealSensitiveValue:
    """Returns an unmasked personal data value and records who saw it (security event
    ``sensitive_data.revealed``). Callers check the record scope (policy) first; this action
    checks the ``*.view_sensitive`` permission (original RevealSensitiveValue)."""

    def __call__(
        self,
        viewer: Any,
        record: models.Model,
        attribute: str,
        permission: str = Permission.PEOPLE_VIEW_SENSITIVE,
        reason: str | None = None,
    ) -> str | None:
        permission = str(permission)
        if not permission.endswith(".view_sensitive") or not viewer.has_perm(permission):
            raise PermissionDenied

        if attribute in encrypted_pii_fields(type(record)):
            value = getattr(record, f"{attribute}{ENCRYPTED_SUFFIX}")
        else:
            value = getattr(record, attribute)

        record_security_event(
            SecurityEventType.SENSITIVE_DATA_REVEALED,
            user=viewer,
            subject=record,
            properties={"attribute": attribute, "reason": reason},
        )
        return None if value is None else str(value)
