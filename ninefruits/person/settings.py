"""Student record options (settings group ``student_records``, original
``App\\Domain\\Person\\Settings\\StudentRecordSettings``)."""

from __future__ import annotations

from typing import ClassVar

from ninefruits.settings.groups.base import SettingsGroup


class StudentRecordSettings(SettingsGroup):
    group: ClassVar[str] = "student_records"

    #: Pattern for new student numbers. Tokens: ``{YYYY}`` ``{YY}`` admission year, ``{SEQ:n}``
    #: sequence of n digits per prefix (everything before ``{SEQ}``). Business rules never read
    #: meaning out of the number; it is only an identifier.
    student_number_pattern: str
    #: Days an account invitation stays valid.
    invitation_valid_days: int
    #: Second majors a student record may have at the same time.
    max_second_majors: int
    #: Minors a student record may have at the same time.
    max_minors: int
