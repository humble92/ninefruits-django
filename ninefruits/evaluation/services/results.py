"""Results of a section's evaluation (original ``EvaluationResults`` and
``SectionEvaluationResult``; legacy counsel/result*.php averaged rounded percentages, skipped
every tenth question and showed results whatever the number of responses).

Answers are shown only when the term's results are published and the section has at least the
minimum responses and response rate; otherwise only the counts, so few responses cannot point to
a student. Means use the raw values, reversed questions counted as (highest point + 1 - value).
Comments come in random order."""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from decimal import ROUND_HALF_UP, Decimal
from typing import Any

from ninefruits.evaluation.enums import QuestionType
from ninefruits.evaluation.models import EvaluationAnswer, EvaluationResponse, TermEvaluation
from ninefruits.security.enums import Permission

_shuffle = random.SystemRandom()


def _round(value: float | Decimal) -> float:
    """Two decimals, half away from zero (PHP ``round``)."""
    return float(Decimal(str(value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))


@dataclass(frozen=True)
class QuestionResult:
    count: int
    mean: float | None
    #: answers per scale point (1..scale points), after reversing
    distribution: dict[int, int]

    def __getitem__(self, key: str) -> Any:
        return getattr(self, key)


@dataclass(frozen=True)
class SectionEvaluationResult:
    """A section's evaluation: response counts always; per question results and comments only
    when shown (published and enough responses)."""

    section: Any
    term_evaluation: TermEvaluation | None
    responses: int
    expected: int
    rate_percent: int
    shown: bool
    #: by question id (scale questions)
    questions: dict[int, QuestionResult] = field(default_factory=dict)
    #: by question id (text questions), in random order
    comments: dict[int, list[str]] = field(default_factory=dict)
    overall_mean: float | None = None
    form_questions: list[Any] = field(default_factory=list)


def expected_responses(section_id: int) -> int:
    """Registered or completed students whose course requires an evaluation."""
    from ninefruits.registration.enums import EnrollmentStatus
    from ninefruits.registration.models import Enrollment

    return Enrollment.objects.filter(
        section_id=section_id,
        status__in=[EnrollmentStatus.ENROLLED, EnrollmentStatus.COMPLETED],
        version__requires_evaluation=True,
    ).count()


def rate(responses: int, expected: int) -> int:
    return 0 if expected == 0 else responses * 100 // expected


class EvaluationResults:
    def can_view(self, section: Any, user: Any) -> bool:
        """Staff with ``evaluations.view`` or ``evaluations.manage`` for the offering unit see the
        counts any time and the answers once published; instructors see their sections once the
        term's results are published."""
        if section.is_in_scope_of(user, Permission.EVALUATIONS_VIEW) or section.is_in_scope_of(
            user, Permission.EVALUATIONS_MANAGE
        ):
            return True
        return (
            section.is_taught_by(user)
            and TermEvaluation.objects.filter(term_id=section.term_id, results_published_at__isnull=False).exists()
        )

    def for_section(self, section: Any) -> SectionEvaluationResult:
        term_evaluation = TermEvaluation.objects.select_related("form").filter(term_id=section.term_id).first()
        responses = EvaluationResponse.objects.filter(section_id=section.pk).count()
        expected = expected_responses(section.pk)
        percent = rate(responses, expected)
        # Answers only after publication (for staff too: following live results during the period
        # against completion times could point to students), and only with enough responses.
        enough = (
            term_evaluation is not None
            and term_evaluation.results_published_at is not None
            and responses > 0
            and responses >= term_evaluation.minimum_responses
            and percent >= term_evaluation.minimum_response_percent
        )
        if not enough or term_evaluation is None:
            return SectionEvaluationResult(section, term_evaluation, responses, expected, percent, False)

        form = term_evaluation.form
        questions_of_form = form.ordered_questions()
        given: dict[int, list[EvaluationAnswer]] = {}
        answers = EvaluationAnswer.objects.filter(
            response_id__in=EvaluationResponse.objects.filter(section_id=section.pk).values("pk")
        )
        for answer in answers:
            given.setdefault(answer.question_id, []).append(answer)

        questions: dict[int, QuestionResult] = {}
        comments: dict[int, list[str]] = {}
        for question in questions_of_form:
            rows = given.get(question.pk, [])
            if question.question_type == QuestionType.TEXT:
                texts = [answer.comment for answer in rows if answer.comment]
                _shuffle.shuffle(texts)
                comments[question.pk] = texts
                continue
            values = [
                form.scale_points + 1 - answer.value if question.is_reversed else answer.value
                for answer in rows
                if answer.value is not None
            ]
            distribution = {point: values.count(point) for point in range(1, form.scale_points + 1)}
            questions[question.pk] = QuestionResult(
                count=len(values),
                mean=_round(Decimal(sum(values)) / len(values)) if values else None,
                distribution=distribution,
            )

        means = [result.mean for result in questions.values() if result.mean is not None]
        overall = _round(Decimal(str(sum(Decimal(str(m)) for m in means))) / len(means)) if means else None
        return SectionEvaluationResult(
            section,
            term_evaluation,
            responses,
            expected,
            percent,
            True,
            questions,
            comments,
            overall,
            questions_of_form,
        )
