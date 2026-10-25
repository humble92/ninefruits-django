"""The students of a section for its instructors and the staff who see the section (original
``App\\Domain\\Attendance\\Services\\SectionRoster``): enrolled and completed enrollments with the
person, program and unit, and the roster as a CSV.

The roster shows only the photo, student number, name, program, year and contact email; national
identifiers, addresses and guardians stay out (ADR 0015)."""

from __future__ import annotations

import csv
import io
import re
from typing import Any

from django.core.exceptions import PermissionDenied
from django.utils.text import capfirst
from django.utils.translation import gettext as _
from django.utils.translation import pgettext

from ninefruits.security.enums import Permission

#: A cell starting with one of these would run as a formula in a spreadsheet (CSV injection).
_FORMULA_START = re.compile(r"^[=+\-@\t\r]")


def spreadsheet_cell(value: Any) -> str:
    """Text for a CSV cell that a spreadsheet will not run as a formula (original
    ``ReportCatalog::cell``): ``None`` is empty, booleans ``Y``/``N``, and text starting with
    ``=``, ``+``, ``-``, ``@``, a tab or a carriage return gets a leading apostrophe."""
    if value is None:
        text = ""
    elif isinstance(value, bool):
        text = "Y" if value else "N"
    else:
        text = str(value)
    return f"'{text}" if _FORMULA_START.match(text) else text


class SectionRoster:
    def enrollments(self, section: Any) -> list[Any]:
        """Enrolled and completed students, by student number."""
        from ninefruits.registration.enums import EnrollmentStatus
        from ninefruits.registration.models import Enrollment

        rows = Enrollment.objects.filter(
            section_id=section.pk, status__in=[EnrollmentStatus.ENROLLED, EnrollmentStatus.COMPLETED]
        ).select_related("student_record__person", "student_record__program", "student_record__org_unit")
        return sorted(rows, key=lambda enrollment: enrollment.student_record.student_number)

    @staticmethod
    def can_view(section: Any, user: Any) -> bool:
        return bool(
            section.is_taught_by(user)
            or section.is_in_scope_of(user, Permission.SECTIONS_VIEW)
            or section.is_in_scope_of(user, Permission.SECTIONS_MANAGE)
        )

    @staticmethod
    def authorize_view(section: Any, user: Any) -> None:
        if not SectionRoster.can_view(section, user):
            raise PermissionDenied

    def csv(self, section: Any) -> str:
        """UTF-8 CSV with a byte order mark so that spreadsheets open it correctly."""
        from ninefruits.registration.enums import EnrollmentStatus

        buffer = io.StringIO()
        buffer.write("﻿")
        writer = csv.writer(buffer, lineterminator="\n")
        writer.writerow(
            [
                _("Student number"),
                pgettext("people", "Name"),
                capfirst(_("program")),
                pgettext("people", "Year"),
                _("Contact email"),
                pgettext("registration", "Status"),
            ]
        )
        for enrollment in self.enrollments(section):
            record = enrollment.student_record
            writer.writerow(
                [
                    spreadsheet_cell(value)
                    for value in (
                        record.student_number,
                        record.person.display_name(),
                        record.program.name,
                        str(record.year_level),
                        record.person.email or "",
                        EnrollmentStatus(enrollment.status).label,
                    )
                ]
            )
        return buffer.getvalue()
