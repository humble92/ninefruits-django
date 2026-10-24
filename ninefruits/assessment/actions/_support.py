"""Small helpers shared by the examination actions."""

from __future__ import annotations

from datetime import datetime
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation
from typing import Any

from django.core.exceptions import ValidationError
from django.utils import timezone
from django.utils.translation import gettext as _

ONE_DECIMAL = Decimal("0.1")


def now() -> datetime:
    """Whole seconds: the columns are ``timestamptz(0)``."""
    return timezone.now().replace(microsecond=0)


def require_reason(value: str | None, field: str = "reason") -> str:
    """The original ``registration.errors.reason_required``."""
    text = (value or "").strip()
    if not text:
        raise ValidationError({field: _("Enter a reason.")})
    return text


def to_decimal(value: Any) -> Decimal | None:
    """A number from a form, CSV cell or JSON value (``is_numeric`` in the original); ``None`` for
    empty or non-numeric input."""
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, Decimal):
        return value
    text = str(value).strip()
    if text == "":
        return None
    try:
        number = Decimal(text)
    except InvalidOperation:
        return None
    return number if number.is_finite() else None


def one_decimal(value: Decimal) -> Decimal:
    """Rounded like the ``numeric(6,1)`` columns round (half away from zero)."""
    return value.quantize(ONE_DECIMAL, rounding=ROUND_HALF_UP)


def json_number(value: Decimal | float | int | None) -> int | float | None:
    """A JSON number for the audit (``55`` rather than ``"55.0"``)."""
    if value is None:
        return None
    number = Decimal(str(value))
    return int(number) if number == number.to_integral_value() else float(number)


def json_value(value: Any) -> Any:
    """Audit and correction payloads: decimals as numbers, the rest unchanged."""
    if isinstance(value, Decimal):
        return json_number(value)
    if isinstance(value, dict):
        return {str(key): json_value(item) for key, item in value.items()}
    if isinstance(value, list | tuple):
        return [json_value(item) for item in value]
    return value
