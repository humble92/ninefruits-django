from __future__ import annotations

from collections.abc import Mapping
from datetime import date, time
from typing import Any

from django.core.exceptions import PermissionDenied, ValidationError
from django.utils.translation import gettext as _
from django.utils.translation import pgettext

from ninefruits.offering.enums import SectionStatus
from ninefruits.offering.models import Section, SectionMeeting
from ninefruits.offering.services import ScheduleConflicts


def _date(value: Any) -> date | None:
    if value in (None, ""):
        return None
    return value if isinstance(value, date) else date.fromisoformat(str(value)[:10])


def _time(value: Any) -> time:
    if isinstance(value, time):
        return value.replace(second=0, microsecond=0)
    hours, minutes = (int(part) for part in str(value).split(":")[:2])
    return time(hours, minutes)


class SaveSectionMeeting:
    """Adds or changes a weekly meeting. Dates default to the section's session; the database
    refuses a room or instructor that is already booked, and the error names the other section."""

    def __init__(self, conflicts: ScheduleConflicts | None = None) -> None:
        self.conflicts = conflicts or ScheduleConflicts()

    def __call__(
        self, section: Section, data: Mapping[str, Any], user: Any, meeting: SectionMeeting | None = None
    ) -> SectionMeeting:
        if not section.is_manageable_by(user):
            raise PermissionDenied

        session = section.session
        start = _date(data.get("start_date")) or session.start_date
        end = _date(data.get("end_date")) or session.end_date
        if start < session.start_date or end > session.end_date or end < start:
            raise ValidationError({"start_date": _("Meeting dates must be within the session.")})

        start_time, end_time = _time(data["start_time"]), _time(data["end_time"])
        if end_time <= start_time:
            raise ValidationError({"end_time": pgettext("offering", "The end must be after the start.")})

        meeting = meeting or SectionMeeting(section=section)
        meeting.weekday = int(data["weekday"])
        meeting.start_time = start_time
        meeting.end_time = end_time
        meeting.room_id = data.get("room_id") or None
        meeting.start_date = start
        meeting.end_date = end
        meeting.is_active = section.status != SectionStatus.CANCELLED

        def change() -> SectionMeeting:
            meeting.save()
            return meeting

        return self.conflicts.guard(change, "room_id")
