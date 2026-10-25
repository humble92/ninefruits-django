"""Student numbers from the configured pattern (original ``StudentNumberGenerator``), e.g.
``{YYYY}{SEQ:5}`` -> ``202600001``.

The sequence is per prefix (the text before ``{SEQ}``) and advanced with one atomic upsert, so
concurrent registrations never get the same number. The number is an identifier only: no rule
reads meaning from its digits (porting-plan 10.1)."""

from __future__ import annotations

import re

from django.db import connection

from ninefruits.person.settings import StudentRecordSettings

_PATTERN = re.compile(r"^(.*)\{SEQ:(\d{1,2})\}(.*)$")

_RESERVE_SQL = (
    "INSERT INTO student_number_sequences (prefix, last_value, created_at, updated_at) "
    "VALUES (%s, %s, now(), now()) "
    "ON CONFLICT (prefix) DO UPDATE SET last_value = student_number_sequences.last_value + EXCLUDED.last_value, "
    "updated_at = now() RETURNING last_value"
)

_NEXT_VALUE_SQL = (
    "INSERT INTO student_number_sequences (prefix, last_value, created_at, updated_at) "
    "VALUES (%s, 1, now(), now()) "
    "ON CONFLICT (prefix) DO UPDATE SET last_value = student_number_sequences.last_value + 1, updated_at = now() "
    "RETURNING last_value"
)


def student_number_exists(number: str) -> bool:
    """Whether any record uses the number, including records the caller cannot see
    (``util.student_number_exists`` is SECURITY DEFINER)."""
    with connection.cursor() as cursor:
        cursor.execute("SELECT util.student_number_exists(%s)", [number])
        row = cursor.fetchone()
    return bool(row and row[0])


class StudentNumberGenerator:
    def __init__(self, settings: StudentRecordSettings | None = None) -> None:
        self.settings = settings or StudentRecordSettings.load()

    def next(self, admission_year: int) -> str:
        prefix, digits, suffix = self._parts(admission_year)
        while True:
            with connection.cursor() as cursor:
                cursor.execute(_NEXT_VALUE_SQL, [prefix])
                value = int(cursor.fetchone()[0])
            number = f"{prefix}{str(value).zfill(digits)}{suffix}"
            # Numbers entered by hand or imported may already use a value; skip those.
            if not student_number_exists(number):
                return number

    def next_many(self, admission_year: int, count: int) -> list[str]:
        """``count`` numbers at once with one upsert per block (bulk data such as the demo
        seeder). Numbers already used are skipped, like :meth:`next`."""
        prefix, digits, suffix = self._parts(admission_year)
        numbers: list[str] = []
        while len(numbers) < count:
            wanted = count - len(numbers)
            with connection.cursor() as cursor:
                cursor.execute(_RESERVE_SQL, [prefix, wanted])
                last = int(cursor.fetchone()[0])
            block = [f"{prefix}{str(value).zfill(digits)}{suffix}" for value in range(last - wanted + 1, last + 1)]
            from ninefruits.person.models import StudentRecord

            taken = set(StudentRecord.objects.filter(student_number__in=block).values_list("student_number", flat=True))
            numbers.extend(number for number in block if number not in taken)
        return numbers

    def _parts(self, admission_year: int) -> tuple[str, int, str]:
        pattern = self.settings.student_number_pattern
        match = _PATTERN.match(pattern)
        if match is None:
            raise ValueError(f"The student number pattern [{pattern}] needs exactly one {{SEQ:n}} token.")
        before, digits, after = match.groups()
        return self._expand(before, admission_year), int(digits), self._expand(after, admission_year)

    @staticmethod
    def _expand(text: str, year: int) -> str:
        return text.replace("{YYYY}", str(year)).replace("{YY}", str(year)[-2:])
