"""Term close (original ``CloseTerm``; legacy: none, warnings and honors were reports over live
views): every grade of the term finalized, then per chunk of students the term record, academic
standing and honors eligibility (a Celery chord of ``grading.close_term_records`` tasks, progress
in ``job_batches``), then honors ranks per program, the records closed as the official snapshot
and the term moved to grades closed (``grading.finish_term_close``, porting-plan 10 and 13.1)."""

from __future__ import annotations

from collections import defaultdict
from typing import Any

from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.db.models import Count, Q
from django.utils.translation import gettext as _

from ninefruits.audit.logger import audit
from ninefruits.core.batches import JobBatch
from ninefruits.core.db import session_context
from ninefruits.grading.data import OpenSection, TermClosePreflight
from ninefruits.grading.enums import AcademicStanding, GradeStatus
from ninefruits.grading.models import TermRecord
from ninefruits.grading.services.term_records import AcademicStandingJudge, TermRecordCalculator
from ninefruits.grading.settings import GradingSettings
from ninefruits.security.enums import Permission
from ninefruits.term.enums import TermStatus

from ._support import now

#: Students per ``grading.close_term_records`` task (original ``CHUNK``).
CHUNK = 100
BATCH_PREFIX = "term-close:"


def batch_name(term: Any) -> str:
    return f"{BATCH_PREFIX}{term.code}"


class CloseTerm:
    def __init__(self, settings: GradingSettings | None = None) -> None:
        self.settings = settings or GradingSettings.load()
        self.records = TermRecordCalculator()
        self.standing = AcademicStandingJudge(self.settings)

    # -- check -------------------------------------------------------------------------------------
    def preflight(self, term: Any) -> TermClosePreflight:
        from ninefruits.offering.models import Section
        from ninefruits.registration.enums import EnrollmentStatus
        from ninefruits.registration.models import Enrollment

        sections = (
            Section.objects.filter(term_id=term.pk)
            .annotate(unfinished=Count("enrollments", filter=Q(enrollments__status=EnrollmentStatus.ENROLLED)))
            .filter(unfinished__gt=0)
            .select_related("course", "version")
        )
        open_sections = sorted(
            (OpenSection(section, int(section.unfinished)) for section in sections),
            key=lambda entry: entry.section.label(),
        )
        students = (
            Enrollment.objects.filter(term_id=term.pk, grade_status=GradeStatus.FINALIZED)
            .values("student_record_id")
            .distinct()
            .count()
        )
        return TermClosePreflight(term, open_sections, students)

    # -- start ----------------------------------------------------------------------------------------
    def close(self, term: Any, staff: Any, reason: str | None = None) -> JobBatch | None:
        """Starts the close; it finishes in the queue (after the surrounding transaction commits).
        ``staff`` is ``None`` for a console run. Returns the batch (``None`` without students)."""
        from ninefruits.grading.tasks import close_term_records, finish_term_close
        from ninefruits.registration.models import Enrollment

        if staff is not None and not staff.has_perm(Permission.GRADES_MANAGE):
            raise PermissionDenied
        if term.status != TermStatus.PUBLISHED:
            raise ValidationError({"term": _("Only a published term closes.")})
        preflight = self.preflight(term)
        if not preflight.is_ready():
            raise ValidationError(
                {
                    "term": _("%(count)s section(s) have grades that are not final.")
                    % {"count": len(preflight.open_sections)}
                }
            )
        reason = (reason or "").strip() or None
        audit("term.close_started", term, reason=reason, properties={"students": preflight.students}, causer=staff)

        record_ids = sorted(
            set(
                Enrollment.objects.filter(term_id=term.pk, grade_status=GradeStatus.FINALIZED).values_list(
                    "student_record_id", flat=True
                )
            )
        )
        chunks = [record_ids[start : start + CHUNK] for start in range(0, len(record_ids), CHUNK)]
        staff_id = staff.pk if staff is not None else None
        batch = JobBatch.start(batch_name(term), len(chunks), {"term_id": term.pk, "user_id": staff_id})
        finish = finish_term_close.si(batch.pk, term.pk, staff_id, reason)

        def dispatch() -> None:
            from celery import chord

            if not chunks:
                finish.apply_async()
                return
            chord(close_term_records.si(batch.pk, term.pk, chunk) for chunk in chunks)(finish)

        transaction.on_commit(dispatch)
        return batch

    # -- per chunk ------------------------------------------------------------------------------------
    def close_records(self, term: Any, record_ids: list[int]) -> int:
        """Term records, standing and honors eligibility of the students. Returns the number of
        records written."""
        from ninefruits.person.models import StudentRecord
        from ninefruits.registration.models import Enrollment

        with session_context().system("grading.close_term"), transaction.atomic():
            calculated = self.records.recalculate_many(record_ids, term)
            earlier = self.standing.earlier_standings(record_ids, term)
            failing = set(
                Enrollment.objects.filter(
                    student_record_id__in=record_ids,
                    term_id=term.pk,
                    grade_status=GradeStatus.FINALIZED,
                    is_passed=False,
                ).values_list("student_record_id", flat=True)
            )
            at = now()
            updated: list[TermRecord] = []
            standings: dict[str, list[int]] = defaultdict(list)
            for record_id in record_ids:
                record = calculated.get(record_id, {}).get(term.pk)
                if record is None:
                    continue
                self.standing.judge(record, term, earlier.get(record_id, []))
                record.is_honors = self._honors_eligible(record, term, record_id in failing)
                record.honors_rank = None
                record.updated_at = at
                updated.append(record)
                if record.academic_standing is not None:
                    standings[str(record.academic_standing)].append(record_id)
            TermRecord.objects.bulk_update(
                updated,
                ["academic_standing", "warning_count", "is_honors", "honors_rank", "updated_at"],
                batch_size=500,
            )
            for standing, ids in standings.items():
                StudentRecord.objects.filter(pk__in=ids).update(academic_standing=standing, updated_at=at)
        return len(updated)

    # -- finish ---------------------------------------------------------------------------------------
    def finish(self, term: Any, staff: Any, reason: str | None) -> dict[str, int]:
        from ninefruits.term.actions import ChangeTermStatus

        with session_context().system("grading.close_term"), transaction.atomic():
            self._rank_honors(term)
            TermRecord.objects.filter(term_id=term.pk).update(closed_at=now())
            term.refresh_from_db()
            if term.status == TermStatus.PUBLISHED:
                ChangeTermStatus()(term, TermStatus.GRADES_CLOSED, reason, staff)
            records = TermRecord.objects.filter(term_id=term.pk)
            counts = {
                "records": records.count(),
                "warnings": records.filter(academic_standing=AcademicStanding.WARNING).count(),
                "dismissal_reviews": records.filter(academic_standing=AcademicStanding.DISMISSAL_REVIEW).count(),
                "honors": records.filter(is_honors=True).count(),
            }
            audit("term.closed", term, reason=reason, properties=counts, causer=staff)
        return counts

    def _honors_eligible(self, record: TermRecord, term: Any, has_failed_course: bool) -> bool:
        settings = self.settings
        if settings.standing_regular_terms_only and not term.term_type.is_regular:
            return False
        if record.term_gpa is None or record.term_gpa < GradingSettings.decimal(settings.honors_min_gpa):
            return False
        if record.gpa_credits < GradingSettings.decimal(settings.honors_min_credits):
            return False
        return not (settings.honors_exclude_failing and has_failed_course)

    def _rank_honors(self, term: Any) -> None:
        """Ranks honors students per program by term GPA (1, 1, 3 on ties)."""
        by_program: dict[int, list[TermRecord]] = defaultdict(list)
        for record in TermRecord.objects.filter(term_id=term.pk, is_honors=True).select_related("student_record"):
            by_program[record.student_record.program_id].append(record)
        at = now()
        ranked: list[TermRecord] = []
        for records in by_program.values():
            records.sort(key=lambda record: (-(record.term_gpa or 0), record.student_record_id))
            rank, previous = 0, None
            for index, record in enumerate(records):
                if record.term_gpa != previous:
                    rank, previous = index + 1, record.term_gpa
                record.honors_rank = rank
                record.updated_at = at
                ranked.append(record)
        TermRecord.objects.bulk_update(ranked, ["honors_rank", "updated_at"], batch_size=500)
