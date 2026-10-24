"""Attendance for one meeting (original ``App\\Domain\\Attendance\\Actions\\RecordAttendance``): a
status per enrolled student (present, late, absent, excused), entered by the instructors or staff.
Entering again replaces; only changed students are written, and the audit record keeps the
previous and new status of each. An empty status clears the record (not recorded)."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone
from django.utils.translation import gettext as _

from ninefruits.attendance.actions.manage_class_meetings import ManageClassMeetings
from ninefruits.attendance.enums import AttendanceStatus, ClassMeetingStatus
from ninefruits.attendance.models import AttendanceRecord, ClassMeeting
from ninefruits.audit.logger import audit

NOTE_MAX = 200


def _int(value: Any) -> int | None:
    try:
        return int(value)
    except TypeError, ValueError:
        return None


def _note(value: Any) -> str | None:
    text = "" if value is None else str(value).strip()
    return text[:NOTE_MAX] if text else None


class RecordAttendance:
    def save(
        self,
        meeting: ClassMeeting,
        statuses: Mapping[int, str | None],
        user: Any,
        notes: Mapping[int, str | None] | None = None,
    ) -> int:
        """``statuses``: enrollment id -> status value (``None``/empty clears); ``notes``:
        enrollment id -> note. Returns the number of records written."""
        from ninefruits.registration.enums import EnrollmentStatus
        from ninefruits.registration.models import Enrollment

        ManageClassMeetings.authorize(meeting.section, user)
        if meeting.status == ClassMeetingStatus.CANCELLED:
            raise ValidationError({"meeting": _("This meeting is cancelled.")})
        if meeting.meeting_date > timezone.localdate():
            raise ValidationError({"meeting": _("Attendance can be entered from the day of the meeting.")})

        notes_by_id = {_int(key): value for key, value in (notes or {}).items()}
        enrolled = set(
            Enrollment.objects.filter(
                section_id=meeting.section_id, status__in=[EnrollmentStatus.ENROLLED, EnrollmentStatus.COMPLETED]
            ).values_list("pk", flat=True)
        )
        before = {record.enrollment_id: record for record in AttendanceRecord.objects.filter(class_meeting=meeting)}
        changes: dict[int, list[str | None]] = {}
        written = 0
        now = timezone.now().replace(microsecond=0)

        with transaction.atomic():
            for raw_id, value in statuses.items():
                enrollment_id = _int(raw_id)
                if enrollment_id is None or enrollment_id not in enrolled:
                    raise ValidationError({"statuses": _("A student is not enrolled in this section.")})
                previous = before.get(enrollment_id)
                if value is None or value == "":
                    if previous is not None:
                        previous.delete()
                        changes[enrollment_id] = [previous.status, None]
                    continue
                if value not in AttendanceStatus.values:
                    raise ValidationError({"statuses": _("Unknown attendance status.")})
                note = _note(notes_by_id.get(enrollment_id))
                if previous is not None and previous.status == value and previous.note == note:
                    continue
                changes[enrollment_id] = [previous.status if previous is not None else None, value]
                if previous is None:
                    AttendanceRecord.objects.create(
                        class_meeting=meeting,
                        enrollment_id=enrollment_id,
                        status=value,
                        note=note,
                        recorded_by_id=user.pk,
                        recorded_at=now,
                    )
                else:
                    previous.status = value
                    previous.note = note
                    previous.recorded_by_id = user.pk
                    previous.recorded_at = now
                    previous.save(update_fields=["status", "note", "recorded_by", "recorded_at", "updated_at"])
                written += 1

        if changes:
            audit(
                "attendance.recorded",
                meeting,
                properties={
                    "section_id": meeting.section_id,
                    "date": meeting.meeting_date.isoformat(),
                    "changes": changes,
                },
                causer=user,
            )
        return written
