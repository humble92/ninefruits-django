"""Serial numbers from the configured pattern (original ``CertificateSerialGenerator``), e.g.
``{TYPE}-{YYYY}-{SEQ:6}`` -> ``ENR-2026-000001``.

The sequence is per prefix (the text before ``{SEQ}`` with its tokens filled in) and advanced
with one atomic upsert, so two issues never share a number, even when issued at the same moment
(the legacy counted ``MAX+1`` without a lock). A failed issue skips its number: uniqueness over
continuity (ADR 0013)."""

from __future__ import annotations

import re
from datetime import datetime

from django.db import connection
from django.utils import timezone

from ninefruits.certificate.settings import CertificateSettings

_PATTERN = re.compile(r"^(.*)\{SEQ:(\d{1,2})\}(.*)$")

_NEXT_VALUE_SQL = (
    "INSERT INTO certificate_number_sequences (prefix, last_value, created_at, updated_at) "
    "VALUES (%s, 1, now(), now()) "
    "ON CONFLICT (prefix) DO UPDATE SET last_value = certificate_number_sequences.last_value + 1, updated_at = now() "
    "RETURNING last_value"
)


def institution_now(at: datetime | None = None) -> datetime:
    """``at`` (default: now) in the institution's time zone (the issue year and date)."""
    from ninefruits.term.services import TermResolver

    return timezone.localtime(at or timezone.now(), TermResolver().zone())


class CertificateSerialGenerator:
    def __init__(self, settings: CertificateSettings | None = None) -> None:
        self._settings = settings

    @property
    def settings(self) -> CertificateSettings:
        if self._settings is None:
            self._settings = CertificateSettings.load()
        return self._settings

    def next(self, type_code: str, at: datetime | None = None) -> str:
        """The next serial number for a kind (its code) issued at ``at`` (default: now)."""
        pattern = self.settings.serial_pattern
        match = _PATTERN.match(pattern)
        if match is None:
            raise ValueError(f"The certificate serial pattern [{pattern}] needs exactly one {{SEQ:n}} token.")
        before, digits, after = match.groups()
        year = institution_now(at).year
        prefix = self._expand(before, type_code, year)
        with connection.cursor() as cursor:
            cursor.execute(_NEXT_VALUE_SQL, [prefix])
            value = int(cursor.fetchone()[0])
        return f"{prefix}{str(value).zfill(int(digits))}{self._expand(after, type_code, year)}"

    @staticmethod
    def _expand(text: str, type_code: str, year: int) -> str:
        return text.replace("{TYPE}", type_code).replace("{YYYY}", str(year)).replace("{YY}", str(year)[-2:])
