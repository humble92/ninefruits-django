"""Weekly timetables (original ``App\\Domain\\Offering\\Services\\Timetable``).

Turns meetings into a weekly grid: one column per weekday that has meetings (Monday to Friday
always), rows from the earliest start to the latest end in 30-minute steps. Used by the
instructor, room and student timetables (admin page, portal teaching page, registration)."""

from __future__ import annotations

import math
from collections.abc import Callable, Iterable
from typing import Any

from django.utils.translation import gettext as _

from ninefruits.offering.models import SectionMeeting

STEP_MINUTES = 30


def weekday_label(weekday: int) -> str:
    labels = {1: _("Mon"), 2: _("Tue"), 3: _("Wed"), 4: _("Thu"), 5: _("Fri"), 6: _("Sat"), 7: _("Sun")}
    return str(labels.get(int(weekday), weekday))


def weekday_choices() -> list[tuple[int, str]]:
    return [(day, weekday_label(day)) for day in range(1, 8)]


def room_label(meeting: SectionMeeting) -> str:
    """Building code and room number, e.g. "E-201"; empty without a room."""
    room = meeting.room
    return "" if room is None else f"{room.building.code}-{room.code}"


def summary(meetings: Iterable[SectionMeeting]) -> str:
    """The weekly schedule, e.g. "Mon 09:00–10:15 E-201, Wed 09:00–10:15 E-201" (rooms with their
    building loaded)."""
    return ", ".join(
        " ".join(part for part in (weekday_label(m.weekday), m.time_label(), room_label(m)) if part) for m in meetings
    )


def _clock(total: int) -> str:
    return f"{total // 60:02d}:{total % 60:02d}"


class Timetable:
    STEP_MINUTES = STEP_MINUTES

    def build(
        self,
        meetings: Iterable[SectionMeeting],
        describe: Callable[[SectionMeeting], tuple[str, str]],
    ) -> dict[str, Any]:
        """``describe(meeting)`` gives the title and subtitle of an entry."""
        active = [meeting for meeting in meetings if meeting.is_active]
        weekdays = sorted({*[int(m.weekday) for m in active], 1, 2, 3, 4, 5})
        start = min((m.start_minute() for m in active), default=9 * 60)
        end = max((m.end_minute() for m in active), default=18 * 60)
        start = start // STEP_MINUTES * STEP_MINUTES
        end = math.ceil(end / STEP_MINUTES) * STEP_MINUTES
        entries = []
        for meeting in active:
            title, subtitle = describe(meeting)
            entries.append(
                {
                    "weekday": int(meeting.weekday),
                    "weekday_label": weekday_label(meeting.weekday),
                    "start": meeting.start_minute(),
                    "end": meeting.end_minute(),
                    "top": (meeting.start_minute() - start) // STEP_MINUTES,
                    "span": max(1, math.ceil((meeting.end_minute() - meeting.start_minute()) / STEP_MINUTES)),
                    "title": title,
                    "subtitle": subtitle,
                    "time": meeting.time_label(),
                    # Grid placement (CSS grid lines, row 1 is the header).
                    "column": weekdays.index(int(meeting.weekday)) + 2,
                    "row": (meeting.start_minute() - start) // STEP_MINUTES + 2,
                }
            )
        entries.sort(key=lambda entry: (entry["weekday"], entry["start"]))
        rows = list(range(start, end, STEP_MINUTES))
        return {
            "weekdays": weekdays,
            "days": [
                {
                    "weekday": day,
                    "label": weekday_label(day),
                    "column": index + 2,
                    "entries": [entry for entry in entries if entry["weekday"] == day],
                }
                for index, day in enumerate(weekdays)
            ],
            "start": start,
            "end": end,
            "rows": rows,
            "row_labels": [
                {"row": index + 2, "label": _clock(minute) if minute % 60 == 0 else ""}
                for index, minute in enumerate(rows)
            ],
            "columns": len(weekdays),
            "entries": entries,
        }
