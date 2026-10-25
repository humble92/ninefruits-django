"""Added meetings (make-up classes) and cancellations (holidays, instructor absence), by the
section's instructors or ``sections.manage`` staff in scope (original
``App\\Domain\\Attendance\\Actions\\ManageClassMeetings``)."""

from __future__ import annotations

from datetime import date, time
from typing import Any

from django import forms
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import IntegrityError, transaction
from django.utils.translation import gettext as _

from ninefruits.attendance.enums import ClassMeetingStatus
from ninefruits.attendance.models import ClassMeeting
from ninefruits.audit.logger import audit
from ninefruits.offering.models import Section

UNIQUE_CONSTRAINT = "class_meetings_section_id_meeting_date_start_time_unique"


def _time(value: time | str, field: str) -> time:
    """A wall-clock time to the minute; text like ``"09:00"`` is parsed (Django's own message
    when it is not a time)."""
    parsed: time
    if isinstance(value, time):
        parsed = value
    else:
        try:
            parsed = forms.TimeField().clean(value)
        except ValidationError as error:
            raise ValidationError({field: error.messages}) from error
    return parsed.replace(second=0, microsecond=0)


class ManageClassMeetings:
    @staticmethod
    def can_manage(section: Section, user: Any) -> bool:
        return bool(section.is_taught_by(user) or section.is_manageable_by(user))

    @staticmethod
    def authorize(section: Section, user: Any) -> None:
        if not ManageClassMeetings.can_manage(section, user):
            raise PermissionDenied(_("Only the section's instructors and the staff who manage it can do this."))

    def add(
        self,
        section: Section,
        meeting_date: date,
        start_time: time | str,
        end_time: time | str,
        user: Any,
        room_id: int | None = None,
        topic: str | None = None,
    ) -> ClassMeeting:
        self.authorize(section, user)
        start, end = _time(start_time, "start_time"), _time(end_time, "end_time")
        if start >= end:
            raise ValidationError({"end_time": _("The end time must be after the start time.")})
        session = section.session
        if meeting_date < session.start_date or meeting_date > session.end_date:
            raise ValidationError({"meeting_date": _("The date is outside the session.")})
        try:
            # A savepoint, so a duplicate does not abort an enclosing transaction.
            with transaction.atomic():
                meeting = ClassMeeting.objects.create(
                    section_id=section.pk,
                    meeting_date=meeting_date,
                    start_time=start,
                    end_time=end,
                    room_id=room_id,
                    topic=topic,
                )
        except IntegrityError as error:
            if UNIQUE_CONSTRAINT not in str(error):
                raise
            raise ValidationError({"meeting_date": _("A meeting at that date and time already exists.")}) from error
        audit(
            "attendance.meeting_added",
            meeting,
            reason=topic,
            properties={"section_id": section.pk, "date": meeting_date.isoformat()},
            causer=user,
        )
        return meeting

    def cancel(self, meeting: ClassMeeting, user: Any, reason: str | None) -> ClassMeeting:
        self.authorize(meeting.section, user)
        if meeting.status == ClassMeetingStatus.CANCELLED:
            raise ValidationError({"status": _("This meeting is already cancelled.")})
        text = (reason or "").strip()
        if not text:
            raise ValidationError({"reason": _("Enter a reason.")})
        meeting.status = ClassMeetingStatus.CANCELLED
        meeting.cancel_reason = text
        meeting.save(update_fields=["status", "cancel_reason", "updated_at"])
        audit(
            "attendance.meeting_cancelled",
            meeting,
            reason=text,
            properties={"section_id": meeting.section_id, "date": meeting.meeting_date.isoformat()},
            causer=user,
        )
        return meeting

    def restore(self, meeting: ClassMeeting, user: Any) -> ClassMeeting:
        self.authorize(meeting.section, user)
        meeting.status = ClassMeetingStatus.SCHEDULED
        meeting.cancel_reason = None
        meeting.save(update_fields=["status", "cancel_reason", "updated_at"])
        audit("attendance.meeting_restored", meeting, properties={"section_id": meeting.section_id}, causer=user)
        return meeting

    def set_topic(self, meeting: ClassMeeting, user: Any, topic: str | None) -> ClassMeeting:
        self.authorize(meeting.section, user)
        text = (topic or "").strip()
        meeting.topic = text[:200] or None
        meeting.save(update_fields=["topic", "updated_at"])
        return meeting
