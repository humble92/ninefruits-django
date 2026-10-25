"""Class meetings from the weekly meeting times (original
``App\\Domain\\Attendance\\Actions\\GenerateClassMeetings``).

One meeting per occurrence of the weekday between the meeting time's start and end dates.
Idempotent: existing meetings (same date and start time) are kept, with their attendance; a
changed meeting time leaves the old meetings for the instructor to cancel. The caller checks who
may generate (instructors and ``sections.manage`` staff, ``ManageClassMeetings.authorize``)."""

from __future__ import annotations

from datetime import date, timedelta
from typing import Any

from django.db import transaction
from django.utils import timezone

from ninefruits.attendance.models import ClassMeeting
from ninefruits.audit.logger import audit
from ninefruits.offering.enums import SectionStatus
from ninefruits.offering.models import Section, SectionMeeting


def _hhmm(value: Any) -> str:
    return value[:5] if isinstance(value, str) else value.strftime("%H:%M")


def _occurrences(pattern: SectionMeeting) -> list[date]:
    """The dates of the pattern's ISO weekday (1 = Monday) from its start to its end date."""
    first = pattern.start_date + timedelta(days=(pattern.weekday - pattern.start_date.isoweekday()) % 7)
    days = []
    day = first
    while day <= pattern.end_date:
        days.append(day)
        day += timedelta(weeks=1)
    return days


class GenerateClassMeetings:
    def for_section(self, section: Section, actor: Any = None) -> int:
        """Creates the missing meetings of the section and returns how many (0 for a cancelled
        section). Audited as ``attendance.meetings_generated`` when an actor is given and
        something was created."""
        if section.status == SectionStatus.CANCELLED:
            return 0
        existing = {
            (meeting_date, _hhmm(start_time))
            for meeting_date, start_time in ClassMeeting.objects.filter(section_id=section.pk).values_list(
                "meeting_date", "start_time"
            )
        }
        now = timezone.now().replace(microsecond=0)
        rows: list[ClassMeeting] = []
        for pattern in SectionMeeting.objects.filter(section_id=section.pk, is_active=True).order_by("id"):
            for day in _occurrences(pattern):
                key = (day, _hhmm(pattern.start_time))
                if key in existing:
                    continue
                existing.add(key)
                rows.append(
                    ClassMeeting(
                        section_id=section.pk,
                        section_meeting_id=pattern.pk,
                        meeting_date=day,
                        start_time=pattern.start_time,
                        end_time=pattern.end_time,
                        room_id=pattern.room_id,
                        created_at=now,
                        updated_at=now,
                    )
                )
        if rows:
            with transaction.atomic():
                ClassMeeting.objects.bulk_create(rows, batch_size=1000)
        if rows and actor is not None:
            audit("attendance.meetings_generated", section, properties={"created": len(rows)}, causer=actor)
        return len(rows)

    def for_term(self, term: Any, actor: Any = None) -> dict[str, int]:
        """Every section of the term that is not cancelled; audited once for the term."""
        summary = {"sections": 0, "created": 0}
        sections = Section.objects.filter(term_id=term.pk).exclude(status=SectionStatus.CANCELLED).order_by("id")
        for section in sections.iterator(chunk_size=500):
            summary["created"] += self.for_section(section, None)
            summary["sections"] += 1
        if actor is not None:
            audit("attendance.meetings_generated", term, properties=summary, causer=actor)
        return summary
