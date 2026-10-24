"""Grade entry for a section (original ``SaveGrades``; legacy prof/opobj_editgo.php, which
overwrote saved grades on any replayed request). Instructors of the section save drafts and
submit while the section's grade entry window is open; staff with ``grades.manage`` for the
section may do so at any time until the grades are finalized. Submitted grades are locked for
instructors (also by row level security)."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.utils.translation import gettext as _

from ninefruits.audit.logger import audit
from ninefruits.grading.enums import GradeStatus
from ninefruits.grading.notifications import send_grade_exception
from ninefruits.grading.services.distribution import GradeDistributionCheck
from ninefruits.grading.services.options import GradeOptions
from ninefruits.security.enums import Permission
from ninefruits.term.enums import TermWindowType
from ninefruits.term.services import TermResolver

from ._support import now

#: Columns that make up a grade (compared to tell whether a row changed).
GRADE_COLUMNS = ("grade_scale_id", "grade_code", "score", "grade_points", "counts_in_gpa", "is_passed", "grade_status")


class SaveGrades:
    def __init__(
        self,
        options: GradeOptions | None = None,
        distribution: GradeDistributionCheck | None = None,
        terms: TermResolver | None = None,
    ) -> None:
        self.options = options or GradeOptions()
        self.distribution = distribution or GradeDistributionCheck(self.options.settings)
        self.terms = terms or TermResolver()

    def save(self, section: Any, grades: Mapping[Any, Mapping[str, Any]], actor: Any) -> int:
        """Absolute evaluation takes scores (the grades follow), relative evaluation grades only
        (``GradeOptions``). ``grades``: ``{enrollment id: {"grade_code": ..., "score": ...}}``.
        Returns the number of grades saved."""
        by_staff = self._authorize(section, actor)
        at = now()
        saved = 0
        wanted = {int(enrollment_id): values for enrollment_id, values in grades.items()}
        with transaction.atomic():
            enrollments = {e.pk: e for e in self.editable(section, by_staff).filter(pk__in=list(wanted))}
            for enrollment_id, values in wanted.items():
                enrollment = enrollments.get(enrollment_id)
                if enrollment is None:
                    raise ValidationError({"grades": _("Some grades can no longer be changed here.")})
                choice = self.options.resolve(enrollment, values.get("grade_code"), values.get("score"))
                was = {column: getattr(enrollment, column) for column in GRADE_COLUMNS}
                for column, value in choice.attributes().items():
                    setattr(enrollment, column, value)
                if choice.is_empty():
                    enrollment.grade_status = GradeStatus.NONE
                elif choice.item is not None and was["grade_status"] == GradeStatus.SUBMITTED:
                    # Staff corrections before finalization keep a submitted grade submitted.
                    enrollment.grade_status = GradeStatus.SUBMITTED
                else:
                    enrollment.grade_status = GradeStatus.DRAFT
                if all(_same(was[column], getattr(enrollment, column)) for column in GRADE_COLUMNS):
                    continue
                # Staff changing a submitted grade: the previous value goes to the audit trail.
                if by_staff and was["grade_status"] == GradeStatus.SUBMITTED:
                    audit(
                        "grades.submitted_changed",
                        enrollment,
                        properties={
                            "section_id": section.pk,
                            "from": {"grade_code": was["grade_code"], "score": _text(was["score"])},
                            "to": {"grade_code": enrollment.grade_code, "score": _text(enrollment.score)},
                        },
                        causer=actor,
                    )
                enrollment.grade_entered_at = at
                enrollment.grade_entered_by_id = actor.pk
                enrollment.save(update_fields=[*GRADE_COLUMNS, "grade_entered_at", "grade_entered_by", "updated_at"])
                saved += 1
        return saved

    def submit(self, section: Any, actor: Any, exception_reason: str | None = None) -> int:
        """Submits every grade of the section; all registered students need a grade. Relative
        grades must follow the grade caps (decided 2026-10-23): instructors cannot submit
        otherwise; staff can, as a recorded exception with a reason, which the reviewers are told
        about and which the section shows from then on."""
        from ninefruits.registration.models import Enrollment

        by_staff = self._authorize(section, actor)
        distribution = self.distribution.for_section(section)
        reason = (exception_reason or "").strip()
        if not distribution.passes():
            if not by_staff:
                raise ValidationError(
                    [
                        _("The grades are outside the institution's grade caps. Adjust them, or ask the office."),
                        *distribution.violations,
                    ]
                )
            if not reason:
                raise ValidationError({"exception_reason": _("Submitting outside the grade caps needs a reason.")})

        with transaction.atomic():
            enrollments = list(self.editable(section, by_staff).exclude(grade_status=GradeStatus.SUBMITTED))
            missing = sum(1 for enrollment in enrollments if enrollment.grade_code is None)
            if missing:
                raise ValidationError({"grades": _("%(count)s student(s) have no grade yet.") % {"count": missing}})
            at = now()
            Enrollment.objects.filter(pk__in=[e.pk for e in enrollments]).update(
                grade_status=GradeStatus.SUBMITTED, grade_submitted_at=at, grade_submitted_by_id=actor.pk
            )
            count = len(enrollments)
            if distribution.passes():
                audit("grades.submitted", section, properties={"count": count}, causer=actor)
            else:
                section.grade_exception_reason = reason
                section.grade_exception_by_id = actor.pk
                section.grade_exception_at = at
                section.save(
                    update_fields=["grade_exception_reason", "grade_exception_by", "grade_exception_at", "updated_at"]
                )
                audit(
                    "grades.submitted_with_exception",
                    section,
                    reason=reason,
                    properties={
                        "count": count,
                        "distribution": distribution.as_dict(),
                        "violations": distribution.violations,
                    },
                    causer=actor,
                )

        if not distribution.passes():
            from ninefruits.security.services.authorization import authorization

            for reviewer in authorization().users_holding(Permission.GRADE_EXCEPTIONS_REVIEW, section.org_unit_id):
                if reviewer.pk != actor.pk:
                    send_grade_exception(reviewer, section, actor, reason, distribution.violations)
        return count

    def can_enter(self, section: Any, user: Any) -> bool:
        """Whether the user may enter the section's grades now (for screens)."""
        try:
            self._authorize(section, user)
        except PermissionDenied, ValidationError:
            return False
        return True

    def is_staff(self, section: Any, user: Any) -> bool:
        return bool(section.is_in_scope_of(user, Permission.GRADES_MANAGE))

    def _authorize(self, section: Any, actor: Any) -> bool:
        """Returns whether the actor acts as staff."""
        if self.is_staff(section, actor):
            return True
        if not section.is_taught_by(actor):
            raise PermissionDenied
        if not self.terms.is_open_in_session(TermWindowType.GRADE_ENTRY, section.session):
            raise ValidationError({"grades": _("Grade entry is not open for this section.")})
        return False

    def editable(self, section: Any, by_staff: bool) -> Any:
        from ninefruits.registration.enums import EnrollmentStatus
        from ninefruits.registration.models import Enrollment

        statuses = [GradeStatus.NONE, GradeStatus.DRAFT] + ([GradeStatus.SUBMITTED] if by_staff else [])
        return Enrollment.objects.filter(
            section_id=section.pk, status=EnrollmentStatus.ENROLLED, grade_status__in=statuses
        ).select_related("version", "section")


def _same(a: Any, b: Any) -> bool:
    if a is None or b is None:
        return a is b
    try:
        from decimal import Decimal

        if isinstance(a, Decimal) or isinstance(b, Decimal):
            return Decimal(a) == Decimal(b)
    except TypeError, ValueError, ArithmeticError:
        pass
    return bool(a == b)


def _text(value: Any) -> str | None:
    return None if value is None else format(value, "f")
