"""Explains double bookings (original ``App\\Domain\\Offering\\Services\\ScheduleConflicts``).

Runs a timetable change and turns the database's double-booking errors (room exclusion
constraint, instructor trigger, overlapping meetings of one section) into messages that name the
other section. The database decides; this only explains."""

from __future__ import annotations

import re
from collections.abc import Callable
from datetime import date, time, timedelta
from typing import Any

from django.core.exceptions import ValidationError
from django.db import DatabaseError, transaction
from django.utils.translation import gettext as _

EXCLUSION_VIOLATION = "23P01"

_INSTRUCTOR = re.compile(r"instructor_conflict instructor=(\d+) section=\d+ other_section=(\d+)")
_ROOM_KEY = re.compile(
    r"conflicts with existing key \(room_id, weekday, time_range, date_range\)=\((\d+), (\d+), "
    r"\[(\d+),(\d+)\), \[([\d-]+),([\d-]+)\)\)"
)


def _sqlstate(error: BaseException) -> str | None:
    cause = error.__cause__ or error
    return getattr(cause, "sqlstate", None) or getattr(getattr(cause, "diag", None), "sqlstate", None)


def _text(error: BaseException) -> str:
    cause = error.__cause__ or error
    detail = getattr(getattr(cause, "diag", None), "message_detail", None) or ""
    return f"{cause}\n{detail}"


class ScheduleConflicts:
    def guard[T](self, change: Callable[[], T], field: str = "schedule") -> T:
        """Runs ``change`` in its own savepoint (a failed statement would otherwise abort the
        caller's transaction) and raises ``ValidationError({field: message})`` for a double
        booking."""
        try:
            with transaction.atomic():
                return change()
        except DatabaseError as error:
            message = self.explain(error)
            if message is None:
                raise
            raise ValidationError({field: message}) from error

    def explain(self, error: BaseException) -> str | None:
        if _sqlstate(error) != EXCLUSION_VIOLATION:
            return None
        text = _text(error)
        match = _INSTRUCTOR.search(text)
        if match:
            from ninefruits.person.models import Instructor

            instructor = Instructor.objects.select_related("person").filter(pk=int(match[1])).first()
            return _("%(instructor)s already teaches %(section)s at this time.") % {
                "instructor": instructor.person.display_name() if instructor is not None else f"#{match[1]}",
                "section": self.section_label(int(match[2])),
            }
        if "section_meetings_room_excl" in text:
            return _("The room is already booked at this time by %(section)s.") % {
                "section": self._conflicting_section(text) or "-"
            }
        if "section_meetings_section_excl" in text:
            return _("This section already meets at an overlapping time.")
        return None

    def _conflicting_section(self, text: str) -> str | None:
        """The DETAIL of an exclusion violation names the existing row's key, e.g. ``(room_id,
        weekday, time_range, date_range)=(5, 1, [540,615), ...) conflicts with existing key
        (...)=(5, 1, [570,630), [2026-09-01,2026-12-21))``."""
        from ninefruits.offering.models import SectionMeeting

        match = _ROOM_KEY.search(text)
        if not match:
            return None
        start, end = int(match[3]), int(match[4])
        meeting = (
            SectionMeeting.objects.filter(
                room_id=int(match[1]),
                weekday=int(match[2]),
                is_active=True,
                start_time=time(start // 60, start % 60),
                end_time=time(end // 60, end % 60),
                start_date=date.fromisoformat(match[5]),
                # daterange '[]' is shown in canonical form [start, end + 1).
                end_date=date.fromisoformat(match[6]) - timedelta(days=1),
            )
            .order_by("id")
            .first()
        )
        return None if meeting is None else self.section_label(meeting.section_id)

    @staticmethod
    def section_label(section_id: int) -> str:
        from ninefruits.offering.models import Section

        section: Any = Section.objects.select_related("course", "term").filter(pk=section_id).first()
        return f"#{section_id}" if section is None else f"{section.label()} ({section.term.code})"
