"""Attendance enums (original ``App\\Domain\\Attendance\\Enums``)."""

from __future__ import annotations

from django.db import models
from django.utils.translation import gettext_lazy as _
from django.utils.translation import pgettext_lazy


class AttendanceStatus(models.TextChoices):
    """Excused: an absence the institution accepts (illness, official business); it does not
    count as absent."""

    PRESENT = "present", _("Present")
    LATE = "late", _("Late")
    ABSENT = "absent", pgettext_lazy("attendance", "Absent")
    EXCUSED = "excused", _("Excused")


class ClassMeetingStatus(models.TextChoices):
    """Cancelled meetings (holidays, instructor absence) are kept but excluded from the
    attendance totals."""

    SCHEDULED = "scheduled", _("Scheduled")
    CANCELLED = "cancelled", pgettext_lazy("attendance", "Cancelled")
