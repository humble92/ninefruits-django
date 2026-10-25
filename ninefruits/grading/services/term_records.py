"""Term records from finalized grades (original ``TermRecordCalculator`` and
``AcademicStandingJudge``, ADR 0011).

A grade change in an earlier term changes every later cumulative value, so records are
recalculated from a term onwards. Standing, honors and the closed time are decided at term close
and kept. Records are derived data written in the system database context: the row level
security policy lets only global ``grades.manage`` write them, while the calculation follows
finalizing and approvals by staff with a scoped grant (callers authorize first). Students are
calculated in bulk (one query for the grades, one upsert for the records), so a term close of
thousands of students stays fast."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable
from typing import Any

from django.utils import timezone

from ninefruits.core.db import session_context
from ninefruits.grading.data import GradedCourse
from ninefruits.grading.enums import AcademicStanding, GradeStatus
from ninefruits.grading.models import TermRecord
from ninefruits.grading.services.gpa import GpaCalculator
from ninefruits.grading.settings import GradingSettings

CALCULATED_FIELDS = [
    "attempted_credits",
    "earned_credits",
    "gpa_credits",
    "grade_points_total",
    "term_gpa",
    "cumulative_attempted_credits",
    "cumulative_earned_credits",
    "cumulative_gpa_credits",
    "cumulative_grade_points_total",
    "cumulative_gpa",
    "calculated_at",
    "updated_at",
]
BATCH = 1000


def finalized_courses(record_ids: Iterable[int]) -> dict[int, list[GradedCourse]]:
    """Finalized grades of the records as the GPA calculation sees them, by record."""
    from ninefruits.registration.models import Enrollment

    rows = Enrollment.objects.filter(
        student_record_id__in=list(record_ids), grade_status=GradeStatus.FINALIZED
    ).values_list(
        "pk",
        "student_record_id",
        "term_id",
        "term__start_date",
        "credits",
        "grade_points",
        "counts_in_gpa",
        "is_passed",
        "repeats_enrollment_id",
    )
    courses: dict[int, list[GradedCourse]] = defaultdict(list)
    for pk, record_id, term_id, start, credits, points, counts, passed, repeats in rows:
        courses[record_id].append(
            GradedCourse(
                enrollment_id=pk,
                term_id=term_id,
                term_start=start.isoformat(),
                credit_tenths=int(credits * 10),
                point_hundredths=None if points is None else int(points * 100),
                counts_in_gpa=bool(counts),
                is_passed=bool(passed),
                repeats_enrollment_id=repeats,
            )
        )
    return courses


class TermRecordCalculator:
    def __init__(self, gpa: GpaCalculator | None = None) -> None:
        self.gpa = gpa or GpaCalculator()

    def recalculate(self, record: Any, from_term: Any = None) -> dict[int, TermRecord]:
        """Recalculates the record's term records from the term on (every term without one).
        Returns the records by term id."""
        return self.recalculate_many([int(record.pk)], from_term).get(int(record.pk), {})

    def recalculate_many(self, record_ids: Iterable[int], from_term: Any = None) -> dict[int, dict[int, TermRecord]]:
        record_ids = list(dict.fromkeys(int(pk) for pk in record_ids))
        if not record_ids:
            return {}
        with session_context().system("grading.term_records"):
            return self._recalculate(record_ids, from_term)

    def _recalculate(self, record_ids: list[int], from_term: Any) -> dict[int, dict[int, TermRecord]]:
        from_start = from_term.start_date.isoformat() if from_term is not None else None
        now = timezone.now().replace(microsecond=0)
        rows: list[TermRecord] = []
        for record_id, courses in finalized_courses(record_ids).items():
            starts = {course.term_id: course.term_start for course in courses}
            for term_id, start in sorted(starts.items(), key=lambda item: (item[1], item[0])):
                if from_start is not None and start < from_start:
                    continue
                term_totals = self.gpa.totals(course for course in courses if course.term_id == term_id)
                cumulative = self.gpa.cumulative([course for course in courses if course.term_start <= start])
                rows.append(
                    TermRecord(
                        student_record_id=record_id,
                        term_id=term_id,
                        attempted_credits=term_totals.attempted_credits,
                        earned_credits=term_totals.earned_credits,
                        gpa_credits=term_totals.gpa_credits,
                        grade_points_total=term_totals.grade_points_total,
                        term_gpa=term_totals.gpa,
                        cumulative_attempted_credits=cumulative.attempted_credits,
                        cumulative_earned_credits=cumulative.earned_credits,
                        cumulative_gpa_credits=cumulative.gpa_credits,
                        cumulative_grade_points_total=cumulative.grade_points_total,
                        cumulative_gpa=cumulative.gpa,
                        calculated_at=now,
                        created_at=now,
                        updated_at=now,
                    )
                )
        TermRecord.objects.bulk_create(
            rows,
            batch_size=BATCH,
            update_conflicts=True,
            unique_fields=["student_record", "term"],
            update_fields=CALCULATED_FIELDS,
        )
        result: dict[int, dict[int, TermRecord]] = defaultdict(dict)
        keys = {(row.student_record_id, row.term_id) for row in rows}
        for stored in TermRecord.objects.filter(student_record_id__in=record_ids):
            if (stored.student_record_id, stored.term_id) in keys:
                result[stored.student_record_id][stored.term_id] = stored
        return dict(result)


class AcademicStandingJudge:
    """Academic standing at term close (legacy report_warn*, report_removal*).

    - Warning: term GPA strictly below the threshold. A term without GPA credits (only P/F) is no
      warning.
    - Dismissal review: the warnings so far (all, or only consecutive ones) reach the count.
    - With "regular terms only", summer and winter terms get no standing and do not break a run
      of consecutive warnings."""

    def __init__(self, settings: GradingSettings | None = None) -> None:
        self.settings = settings or GradingSettings.load()

    def earlier_standings(self, record_ids: Iterable[int], term: Any) -> dict[int, list[AcademicStanding]]:
        """Standings decided before the term, oldest first, by record."""
        rows = (
            TermRecord.objects.filter(
                student_record_id__in=list(record_ids),
                term__start_date__lt=term.start_date,
                academic_standing__isnull=False,
            )
            .order_by("term__start_date", "term_id")
            .values_list("student_record_id", "academic_standing")
        )
        standings: dict[int, list[AcademicStanding]] = defaultdict(list)
        for record_id, standing in rows:
            standings[record_id].append(AcademicStanding(standing))
        return standings

    def judge(self, record: TermRecord, term: Any, earlier: list[AcademicStanding] | None = None) -> TermRecord:
        """Sets ``academic_standing`` and ``warning_count`` on the record (not saved). ``term``
        needs its type."""
        if earlier is None:
            earlier = self.earlier_standings([record.student_record_id], term).get(record.student_record_id, [])
        previous = self._count(earlier)
        if self.settings.standing_regular_terms_only and not term.term_type.is_regular:
            record.academic_standing = None
            record.warning_count = previous
            return record

        warned = record.term_gpa is not None and record.term_gpa < GradingSettings.decimal(
            self.settings.warning_gpa_below
        )
        count = self._count([*earlier, AcademicStanding.WARNING if warned else AcademicStanding.GOOD])
        dismissal = int(self.settings.dismissal_warning_count)
        if not warned:
            standing = AcademicStanding.GOOD
        elif dismissal > 0 and count >= dismissal:
            standing = AcademicStanding.DISMISSAL_REVIEW
        else:
            standing = AcademicStanding.WARNING
        record.academic_standing = standing
        record.warning_count = count
        return record

    def _count(self, standings: list[AcademicStanding]) -> int:
        if not self.settings.dismissal_consecutive_only:
            return sum(1 for standing in standings if standing.is_warning())
        run = 0
        for standing in standings:
            run = run + 1 if standing.is_warning() else 0
        return run
