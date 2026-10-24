"""Degree numbers from the configured pattern (original ``DegreeNumberGenerator``), e.g.
``{PROGRAM}-{YYYY}-{SEQ:5}`` -> ``CS-2026-00001``, one atomic sequence per prefix (the same
mechanism as certificate serials and student numbers). The year is the graduation date's."""

from __future__ import annotations

import re
from datetime import date
from typing import Any

from django.db import connection

from ninefruits.graduation.settings import GraduationSettings

_PATTERN = re.compile(r"^(.*)\{SEQ:(\d{1,2})\}(.*)$")

_NEXT_VALUE_SQL = (
    "INSERT INTO degree_number_sequences (prefix, last_value, created_at, updated_at) "
    "VALUES (%s, 1, now(), now()) "
    "ON CONFLICT (prefix) DO UPDATE SET last_value = degree_number_sequences.last_value + 1, updated_at = now() "
    "RETURNING last_value"
)


class DegreeNumberGenerator:
    def __init__(self, settings: GraduationSettings | None = None) -> None:
        self._settings = settings

    @property
    def settings(self) -> GraduationSettings:
        if self._settings is None:
            self._settings = GraduationSettings.load()
        return self._settings

    def next(self, program: Any, graduated_on: date) -> str:
        pattern = self.settings.degree_number_pattern
        match = _PATTERN.match(pattern)
        if match is None:
            raise ValueError(f"The degree number pattern [{pattern}] needs exactly one {{SEQ:n}} token.")
        before, digits, after = match.groups()
        prefix = self._expand(before, program.code, graduated_on.year)
        with connection.cursor() as cursor:
            cursor.execute(_NEXT_VALUE_SQL, [prefix])
            value = int(cursor.fetchone()[0])
        return f"{prefix}{str(value).zfill(int(digits))}{self._expand(after, program.code, graduated_on.year)}"

    @staticmethod
    def _expand(text: str, program_code: str, year: int) -> str:
        return text.replace("{YYYY}", str(year)).replace("{YY}", str(year)[-2:]).replace("{PROGRAM}", program_code)
