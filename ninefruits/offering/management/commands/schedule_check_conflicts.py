"""Checks a term's sections before publishing the timetable (original
``schedule:check-conflicts``). Double bookings are refused by the database already; this also
finds what the database allows but people should fix."""

from __future__ import annotations

import io
from typing import Any

from django.core.management.base import CommandParser
from django.db import connection
from rich.console import Console
from rich.table import Table

from ninefruits.core.commands import StatusCommand
from ninefruits.offering.enums import SectionStatus
from ninefruits.offering.models import Section
from ninefruits.term.models import Term

# Safety net for rows written while constraints were off (e.g. a restore).
DOUBLE_BOOKINGS = """
    SELECT a.section_id, b.section_id
    FROM section_meetings AS a
    JOIN section_meetings AS b ON a.id < b.id AND a.room_id = b.room_id AND a.weekday = b.weekday
        AND a.time_range && b.time_range AND a.date_range && b.date_range
    JOIN sections AS s ON s.id = a.section_id
    WHERE s.term_id = %s AND a.is_active AND b.is_active
"""


class Command(StatusCommand):
    help = "Check a term's sections: double bookings, rooms too small, versions, instructors, seat groups"

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument("term", help="Term code, e.g. 2027-SP")

    def handle(self, *args: Any, **options: Any) -> int:  # type: ignore[override]  # exit code (StatusCommand)
        term = Term.objects.filter(code=options["term"]).first()
        if term is None:
            self.error("Unknown term code.")
            return self.FAILURE

        sections = list(
            Section.objects.filter(term=term)
            .exclude(status=SectionStatus.CANCELLED)
            .select_related("course", "version", "session")
            .prefetch_related("instructor_assignments__instructor", "meetings__room", "seat_groups")
        )
        problems: list[tuple[str, str]] = []
        notes: list[tuple[str, str]] = []
        for section in sections:
            label = section.label()
            session = section.session
            if not section.version.is_effective_on(session.start_date):
                problems.append((label, "course version not in effect when the session starts"))
            if sum(group.capacity for group in section.seat_groups.all()) > section.capacity:
                problems.append((label, "seat groups exceed the capacity"))
            assignments = list(section.instructor_assignments.all())
            for assignment in assignments:
                if not assignment.instructor.is_current(session.start_date):
                    problems.append(
                        (label, f"instructor {assignment.instructor.employee_number} is no longer employed")
                    )
            meetings = list(section.meetings.all())
            for meeting in meetings:
                room = meeting.room
                if room is not None and room.capacity is not None and room.capacity < section.capacity:
                    problems.append(
                        (label, f"room {room.code} holds {room.capacity}, section capacity {section.capacity}")
                    )
                if meeting.start_date < session.start_date or meeting.end_date > session.end_date:
                    problems.append((label, "meeting dates outside the session"))
                if meeting.room_id is None:
                    notes.append((label, f"meeting {meeting.time_label()} has no room"))
            if not assignments:
                notes.append((label, "no instructor"))
            if not meetings:
                notes.append((label, "no meeting times"))

        with connection.cursor() as cursor:
            cursor.execute(DOUBLE_BOOKINGS, [term.pk])
            for first, second in cursor.fetchall():
                problems.append((f"#{first} / #{second}", "room double-booked"))

        if notes:
            self._table(("Section", "Note"), notes)
        if not problems:
            self.info(f"{len(sections)} section(s) checked, no problems.")
            return self.SUCCESS
        self._table(("Section", "Problem"), problems)
        self.warn(f"{len(problems)} problem(s).")
        return self.PROBLEMS_FOUND

    def _table(self, headers: tuple[str, str], rows: list[tuple[str, str]]) -> None:
        table = Table(*headers)
        for row in rows:
            table.add_row(*row)
        buffer = io.StringIO()
        Console(file=buffer, width=160, force_terminal=False, color_system=None).print(table)
        self.stdout.write(buffer.getvalue().rstrip("\n"))
