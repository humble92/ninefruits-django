"""Small helpers shared by the grading actions."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from django.core.exceptions import ValidationError
from django.utils import timezone
from django.utils.translation import gettext as _


def now() -> datetime:
    """Whole seconds: the columns are ``timestamptz(0)``."""
    return timezone.now().replace(microsecond=0)


def require_reason(value: str | None, field: str = "reason") -> str:
    """The original ``registration.errors.reason_required``."""
    text = (value or "").strip()
    if not text:
        raise ValidationError({field: _("Enter a reason.")})
    return text


def user_id(user: Any) -> int | None:
    return int(user.pk) if user is not None and getattr(user, "pk", None) is not None else None
