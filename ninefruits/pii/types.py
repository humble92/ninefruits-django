"""Kinds of personal data: normalization before hashing and masking for display (original
App\\Support\\Pii\\PiiType)."""

from __future__ import annotations

import re
from enum import StrEnum

_NOT_ALPHANUMERIC = re.compile(r"[^A-Za-z0-9]")
# PHP trim() characters.
_PHP_TRIM = " \t\n\r\0\x0b"


class PiiType(StrEnum):
    NATIONAL_ID = "national_id"
    PASSPORT_NUMBER = "passport_number"
    PHONE_NUMBER = "phone_number"
    EMAIL = "email"
    GENERIC = "generic"

    def normalize(self, value: str) -> str:
        """Normalization before hashing, so that ``900101-1234567`` and ``9001011234567`` match."""
        match self:
            case PiiType.NATIONAL_ID | PiiType.PASSPORT_NUMBER | PiiType.PHONE_NUMBER:
                return _NOT_ALPHANUMERIC.sub("", value).upper()
            case PiiType.EMAIL:
                return value.strip(_PHP_TRIM).lower()
            case _:
                return value.strip(_PHP_TRIM)

    def mask(self, value: str) -> str:
        """``**********4567`` (last four visible); e-mail ``k**@example.com``."""
        if self is PiiType.EMAIL and "@" in value:
            local, domain = value.split("@", 1)
            return local[:1] + "*" * max(len(local) - 1, 1) + "@" + domain

        visible = 4
        if len(value) <= visible:
            return "*" * len(value)
        return "*" * (len(value) - visible) + value[-visible:]
