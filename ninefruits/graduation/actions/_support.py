"""Small helpers shared by the graduation actions."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from django.core.exceptions import PermissionDenied, ValidationError
from django.utils import timezone
from django.utils.translation import gettext as _

from ninefruits.security.enums import Permission


def now() -> datetime:
    """Whole seconds: the columns are ``timestamptz(0)``."""
    return timezone.now().replace(microsecond=0)


def require_reason(value: str | None, field: str = "reason") -> str:
    """The original ``registration.errors.reason_required``."""
    text = (value or "").strip()
    if not text:
        raise ValidationError({field: _("Enter a reason.")})
    return text


def authorize(staff: Any, record: Any, permission: Permission) -> None:
    """The staff member holds the permission and may see the student record (original
    ``$staff->can(...) && $record->isVisibleTo($staff)``)."""
    if staff is None or not staff.has_perm(str(permission)) or not record.is_visible_to(staff):
        raise PermissionDenied
