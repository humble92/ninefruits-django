"""Class meetings and attendance (original ``App\\Models\\Attendance\\ClassMeeting`` and
``AttendanceRecord``, ADR 0015).

The legacy system recorded nothing (``prt_chuxi`` printed an empty sheet). A class meeting is one
class of a section on a date: generated from the weekly meeting times, or added by hand (a make-up
class, ``section_meeting`` empty). Cancelled meetings stay and do not count. An attendance record
is one student's attendance at one meeting, by enrollment, so retakes and registration changes
fit naturally."""

from __future__ import annotations

from datetime import date, time
from typing import Any, Self

from django.conf import settings
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.utils.translation import pgettext_lazy

from ninefruits.attendance.enums import AttendanceStatus, ClassMeetingStatus
from ninefruits.core.models import TimeStampedModel, VisibleQuerySet


def _hhmm(value: time | str) -> str:
    return value[:5] if isinstance(value, str) else value.strftime("%H:%M")


class ClassMeetingQuerySet(VisibleQuerySet):
    def scheduled(self) -> Self:
        return self.filter(status=ClassMeetingStatus.SCHEDULED)

    def held(self, as_of: date | None = None) -> Self:
        """Meetings that took place: scheduled, on or before the day (today by default)."""
        return self.scheduled().filter(meeting_date__lte=as_of or timezone.localdate())

    def visible_to(self, user: Any) -> Self:
        """Schedule information: anyone signed in reads it (RLS ``class_meetings_select``)."""
        if user is None or not getattr(user, "is_authenticated", False):
            return self.none()
        return self


class ClassMeeting(TimeStampedModel):
    section = models.ForeignKey(
        "offering.Section",
        on_delete=models.CASCADE,
        related_name="class_meetings",
        verbose_name=pgettext_lazy("offering", "Section"),
    )
    #: The weekly meeting time this was generated from; empty for an added meeting (make-up class).
    section_meeting = models.ForeignKey(
        "offering.SectionMeeting", on_delete=models.SET_NULL, null=True, blank=True, related_name="class_meetings"
    )
    meeting_date = models.DateField(pgettext_lazy("attendance", "Date"))
    start_time = models.TimeField(pgettext_lazy("attendance", "Start"))
    end_time = models.TimeField(_("End"))
    room = models.ForeignKey(
        "facility.Room",
        on_delete=models.RESTRICT,
        null=True,
        blank=True,
        related_name="class_meetings",
        verbose_name=_("Room"),
    )
    status = models.CharField(
        pgettext_lazy("registration", "Status"),
        max_length=16,
        choices=ClassMeetingStatus.choices,
        default=ClassMeetingStatus.SCHEDULED,
    )
    topic = models.CharField(max_length=200, null=True, blank=True)
    cancel_reason = models.TextField(pgettext_lazy("common", "Reason"), null=True, blank=True)

    objects = ClassMeetingQuerySet.as_manager()

    class Meta:
        db_table = "class_meetings"
        ordering = ["meeting_date", "start_time"]
        verbose_name = _("class meeting")
        verbose_name_plural = _("Class meetings")
        constraints = [
            models.UniqueConstraint(
                fields=["section", "meeting_date", "start_time"],
                name="class_meetings_section_id_meeting_date_start_time_unique",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.meeting_date} {self.time_label()}"

    @property
    def is_cancelled(self) -> bool:
        return self.status == ClassMeetingStatus.CANCELLED

    def time_label(self) -> str:
        """Start and end, e.g. "09:00–10:50"."""
        return f"{_hhmm(self.start_time)}–{_hhmm(self.end_time)}"

    def room_label(self) -> str:
        """Building code and room number, e.g. "E-201"; empty without a room."""
        room = self.room
        return "" if room is None else f"{room.building.code}-{room.code}"


class AttendanceRecordQuerySet(VisibleQuerySet):
    def visible_to(self, user: Any) -> Self:
        """Whoever sees the enrollment (the student, the instructors, staff in scope) sees the
        record (RLS ``attendance_records_enrollment_select``)."""
        from ninefruits.registration.models import Enrollment

        return self.filter(enrollment_id__in=Enrollment.objects.visible_to(user).values("pk"))


class AttendanceRecord(TimeStampedModel):
    class_meeting = models.ForeignKey(ClassMeeting, on_delete=models.CASCADE, related_name="records")
    enrollment = models.ForeignKey(
        "registration.Enrollment", on_delete=models.CASCADE, related_name="attendance_records"
    )
    status = models.CharField(
        pgettext_lazy("attendance.fields", "Attendance"), max_length=16, choices=AttendanceStatus.choices
    )
    note = models.CharField(pgettext_lazy("attendance", "Note"), max_length=200, null=True, blank=True)
    recorded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )
    recorded_at = models.DateTimeField()

    objects = AttendanceRecordQuerySet.as_manager()

    class Meta:
        db_table = "attendance_records"
        ordering = ["id"]
        verbose_name = _("attendance record")
        verbose_name_plural = _("attendance records")
        # The index attendance_records_enrollment_id_index exists in the database (Django limits
        # declared index names to 30 characters, so it is omitted).
        constraints = [
            models.UniqueConstraint(
                fields=["class_meeting", "enrollment"],
                name="attendance_records_class_meeting_id_enrollment_id_unique",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.class_meeting_id}:{self.enrollment_id} {self.status}"
