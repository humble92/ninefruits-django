"""Demo attendance (original ``DemoAttendanceSeeder``).

The current term's class meetings for every section (``GenerateClassMeetings.for_term``, one
bulk insert per section), and the meetings held so far recorded for the enrolled students: mostly
present, some late, absent and excused; the newest held meeting of one section in five is left
unrecorded. The records are decided in memory and written with bulk inserts (thousands of rows,
no business audit), so ``--size=large`` stays fast; the statuses come from the options'
generator, so ``--seed`` reproduces them."""

from __future__ import annotations

from collections import defaultdict
from typing import Any

from django.utils import timezone

from ninefruits.attendance.actions import GenerateClassMeetings
from ninefruits.attendance.enums import AttendanceStatus
from ninefruits.attendance.models import AttendanceRecord, ClassMeeting
from ninefruits.registration.enums import EnrollmentStatus
from ninefruits.registration.models import Enrollment
from ninefruits.setup import conf
from ninefruits.setup.seeders.base import Seeder
from ninefruits.term.enums import TermStatus
from ninefruits.term.models import Term

from .options import current_options

BATCH = 5000


def _status(rng: Any) -> str:
    """85% present; of the rest half late, then 70% absent, else excused (the original's chained
    draws)."""
    if rng.randint(1, 100) <= 85:
        return AttendanceStatus.PRESENT.value
    if rng.randint(1, 100) <= 50:
        return AttendanceStatus.LATE.value
    if rng.randint(1, 100) <= 70:
        return AttendanceStatus.ABSENT.value
    return AttendanceStatus.EXCUSED.value


class DemoAttendanceSeeder(Seeder):
    def run(self) -> None:
        from ninefruits.security.models import User

        recorder = User.objects.filter(email=f"academic-affairs@{conf.DEMO_EMAIL_DOMAIN}").first()
        today = timezone.localdate()
        current = (
            Term.objects.filter(status=TermStatus.PUBLISHED, start_date__lte=today).order_by("-start_date").first()
        )
        if recorder is None or current is None or ClassMeeting.objects.exists():
            return

        GenerateClassMeetings().for_term(current)

        enrollments: dict[int, list[int]] = defaultdict(list)
        for enrollment_id, section_id in (
            Enrollment.objects.filter(term_id=current.pk, status=EnrollmentStatus.ENROLLED)
            .order_by("section_id", "id")
            .values_list("id", "section_id")
        ):
            enrollments[section_id].append(enrollment_id)
        held: dict[int, list[int]] = defaultdict(list)
        for meeting_id, section_id in (
            ClassMeeting.objects.filter(section_id__in=list(enrollments))
            .held(today)
            .order_by("section_id", "meeting_date", "start_time", "id")
            .values_list("id", "section_id")
        ):
            held[section_id].append(meeting_id)

        rng = current_options().rng
        now = timezone.now().replace(microsecond=0)
        rows: list[AttendanceRecord] = []
        for section_id in sorted(held):
            meetings = held[section_id]
            if section_id % 5 == 0:
                meetings = meetings[:-1]
            for meeting_id in meetings:
                for enrollment_id in enrollments[section_id]:
                    rows.append(
                        AttendanceRecord(
                            class_meeting_id=meeting_id,
                            enrollment_id=enrollment_id,
                            status=_status(rng),
                            recorded_by_id=recorder.pk,
                            recorded_at=now,
                            created_at=now,
                            updated_at=now,
                        )
                    )
            if len(rows) >= BATCH:
                AttendanceRecord.objects.bulk_create(rows, batch_size=BATCH)
                rows = []
        if rows:
            AttendanceRecord.objects.bulk_create(rows, batch_size=BATCH)
