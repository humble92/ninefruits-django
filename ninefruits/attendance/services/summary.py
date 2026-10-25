"""The attendance totals (original ``App\\Domain\\Attendance\\Services\\AttendanceSummary``), the one
place the counting rules live (ADR 0015).

Per student: held meetings (scheduled, on or before today), present, late, absent, excused, not
recorded, and the attendance rate (present + late + excused over held, in percent with one
decimal). The institution's own rule (e.g. absences over a third fail) is applied by people, not
here."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable
from datetime import date
from decimal import ROUND_HALF_UP, Decimal
from typing import Any, TypedDict

from django.utils import timezone

from ninefruits.attendance.enums import AttendanceStatus, ClassMeetingStatus
from ninefruits.attendance.models import AttendanceRecord, ClassMeeting


class Counts(TypedDict):
    present: int
    late: int
    absent: int
    excused: int
    missing: int
    rate: float | None


class SectionSummary(TypedDict):
    held: int
    students: dict[int, Counts]


def _rate(attended: int, held: int) -> float | None:
    """Percent with one decimal, halves away from zero (PHP ``round``)."""
    if held == 0:
        return None
    value = (Decimal(attended) * 100 / Decimal(held)).quantize(Decimal("0.1"), rounding=ROUND_HALF_UP)
    return float(value)


class AttendanceSummary:
    def for_section(self, section: Any, enrollments: Iterable[Any], as_of: date | None = None) -> SectionSummary:
        """Counts for each of the enrollments (normally the roster) over the section's held
        meetings."""
        held = list(ClassMeeting.objects.filter(section_id=section.pk).held(as_of).values_list("pk", flat=True))
        by_enrollment: dict[int, list[str]] = defaultdict(list)
        for enrollment_id, status in AttendanceRecord.objects.filter(class_meeting_id__in=held).values_list(
            "enrollment_id", "status"
        ):
            by_enrollment[enrollment_id].append(status)
        students = {
            enrollment.pk: self.counts(by_enrollment.get(enrollment.pk, []), len(held)) for enrollment in enrollments
        }
        return {"held": len(held), "students": students}

    def counts(self, records: Iterable[Any], held: int) -> Counts:
        """``records``: attendance records or their status values, of held meetings only."""
        tally = {status.value: 0 for status in AttendanceStatus}
        for record in records:
            status = record if isinstance(record, str) else record.status
            tally[str(status)] += 1
        recorded = sum(tally.values())
        attended = tally["present"] + tally["late"] + tally["excused"]
        return {
            "present": tally["present"],
            "late": tally["late"],
            "absent": tally["absent"],
            "excused": tally["excused"],
            "missing": max(0, held - recorded),
            "rate": _rate(attended, held),
        }

    @staticmethod
    def is_counted_present(status: str) -> bool:
        return status != AttendanceStatus.ABSENT

    @staticmethod
    def is_held(meeting: ClassMeeting, as_of: date | None = None) -> bool:
        return meeting.status == ClassMeetingStatus.SCHEDULED and meeting.meeting_date <= (
            as_of or timezone.localdate()
        )
