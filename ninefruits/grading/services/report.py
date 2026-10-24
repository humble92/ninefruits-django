"""A student's grades by term for the grade view and the transcript (original ``GradeReport``,
legacy stu/score.php): finalized grades and withdrawals (W), the term records, and which attempts
a retake replaced in the cumulative GPA. Grades not finalized yet are not shown.

Terms can be hidden from the student by providers registered with
:func:`register_hidden_terms` (Phase 7: a term whose course evaluation is open and unfinished,
original ``EvaluationTasks::blockedTermIds``). The grade page shows the provider's notice for
each hidden term::

    from ninefruits.grading.services.report import register_hidden_terms
    register_hidden_terms(
        "evaluation",
        lambda record: [...term ids...],
        notice=lambda term: _("The grades of %(term)s show after you finish its course evaluation.") % {...},
        link=("portal:evaluations", _("Course evaluation")),
    )
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from django.db.models import Q

from ninefruits.grading.enums import GradeStatus
from ninefruits.grading.models import TermRecord
from ninefruits.grading.services.gpa import GpaCalculator
from ninefruits.grading.services.term_records import finalized_courses


@dataclass(frozen=True)
class HiddenTermsProvider:
    terms: Callable[[Any], list[int]]
    notice: Callable[[Any], str] | None = None
    #: ``(url name, label)`` of the page that lifts the restriction
    link: tuple[str, Any] | None = None


@dataclass(frozen=True)
class HiddenTerm:
    term: Any
    notice: str
    link: tuple[str, Any] | None


_hidden_terms: dict[str, HiddenTermsProvider] = {}


def register_hidden_terms(
    key: str,
    terms: Callable[[Any], list[int]],
    *,
    notice: Callable[[Any], str] | None = None,
    link: tuple[str, Any] | None = None,
) -> None:
    """``terms(student_record) -> term ids`` whose grades the student may not see yet."""
    _hidden_terms[key] = HiddenTermsProvider(terms, notice, link)


def unregister_hidden_terms(key: str) -> None:
    _hidden_terms.pop(key, None)


def hidden_term_ids(record: Any) -> list[int]:
    ids: list[int] = []
    for provider in _hidden_terms.values():
        ids.extend(int(term_id) for term_id in provider.terms(record) or [])
    return list(dict.fromkeys(ids))


def hidden_terms(record: Any) -> list[HiddenTerm]:
    """The hidden terms with their notices, for the grade page."""
    from ninefruits.term.models import Term

    found: list[tuple[int, HiddenTermsProvider]] = []
    for provider in _hidden_terms.values():
        found.extend((int(term_id), provider) for term_id in provider.terms(record) or [])
    terms = {term.pk: term for term in Term.objects.filter(pk__in=[term_id for term_id, _p in found])}
    result = []
    for term_id, provider in found:
        term = terms.get(term_id)
        if term is not None:
            result.append(HiddenTerm(term, provider.notice(term) if provider.notice else "", provider.link))
    return result


@dataclass
class TermGrades:
    term: Any
    enrollments: list[Any] = field(default_factory=list)
    record: TermRecord | None = None


class GradeReport:
    def __init__(self, gpa: GpaCalculator | None = None) -> None:
        self._gpa = gpa

    @property
    def gpa(self) -> GpaCalculator:
        if self._gpa is None:
            self._gpa = GpaCalculator()
        return self._gpa

    def terms(self, record: Any, hidden_term_ids: list[int] | None = None) -> list[TermGrades]:
        """Oldest term first."""
        from ninefruits.registration.enums import EnrollmentStatus
        from ninefruits.registration.models import Enrollment

        enrollments = (
            Enrollment.objects.filter(student_record_id=record.pk)
            .exclude(term_id__in=hidden_term_ids or [])
            .filter(Q(grade_status=GradeStatus.FINALIZED) | Q(status=EnrollmentStatus.WITHDRAWN))
            .select_related("term__term_type", "course", "version", "section")
        )
        records = {row.term_id: row for row in TermRecord.objects.filter(student_record_id=record.pk)}
        by_term: dict[int, TermGrades] = {}
        for enrollment in enrollments:
            entry = by_term.setdefault(
                enrollment.term_id, TermGrades(enrollment.term, record=records.get(enrollment.term_id))
            )
            entry.enrollments.append(enrollment)
        for entry in by_term.values():
            entry.enrollments.sort(key=lambda enrollment: enrollment.course.code)
        return sorted(by_term.values(), key=lambda entry: (entry.term.start_date, entry.term.pk))

    def superseded(self, record: Any) -> set[int]:
        """Enrollment ids a retake replaced in the cumulative GPA."""
        return self.gpa.superseded(finalized_courses([record.pk]).get(int(record.pk), []))

    def blocking_hold(self, record: Any) -> Any:
        """A hold that keeps the student from seeing grades (decided 2026-10-22: off by default;
        for unpaid fees or e.g. an academic integrity investigation)."""
        from ninefruits.registration.models import RegistrationHold

        return (
            RegistrationHold.objects.filter(student_record_id=record.pk, blocks_grades=True)
            .in_force()
            .order_by("id")
            .first()
        )

    def latest_record(self, record: Any, hidden_term_ids: list[int] | None = None) -> TermRecord | None:
        return (
            TermRecord.objects.filter(student_record_id=record.pk)
            .exclude(term_id__in=hidden_term_ids or [])
            .select_related("term")
            .order_by("-term__start_date", "-term_id")
            .first()
        )
