"""A student evaluates one of their courses (original ``SubmitEvaluation``; legacy
counsel/student_addgo.php stored the student number with each answer, took any course id and
wrote rows one by one).

The completion records who evaluated which enrollment; the response records the answers for the
section with no student, sequence or time. Both are written in one transaction in the system
context (row level security cannot check a student on an anonymous row), after the checks here.
One response per enrollment (unique completion); no change afterwards."""

from __future__ import annotations

import re
from collections.abc import Mapping
from typing import Any

from django.core.exceptions import PermissionDenied, ValidationError
from django.db import IntegrityError, transaction
from django.utils import timezone
from django.utils.translation import gettext as _

from ninefruits.core.db import session_context
from ninefruits.evaluation.enums import QuestionType
from ninefruits.evaluation.models import (
    EvaluationAnswer,
    EvaluationCompletion,
    EvaluationResponse,
    TermEvaluation,
)
from ninefruits.evaluation.services.tasks import EvaluationTasks
from ninefruits.evaluation.settings import EvaluationSettings

COMMENT_MAX = 2000
_INTEGER = re.compile(r"^[+-]?(0|[1-9][0-9]*)$")  # PHP FILTER_VALIDATE_INT


class SubmitEvaluation:
    def __init__(self, tasks: EvaluationTasks | None = None, settings: EvaluationSettings | None = None) -> None:
        self.tasks = tasks or EvaluationTasks()
        self._settings = settings

    @property
    def settings(self) -> EvaluationSettings:
        if self._settings is None:
            self._settings = EvaluationSettings.load()
        return self._settings

    def __call__(self, enrollment: Any, answers: Mapping[Any, Any], student: Any) -> None:
        """``answers`` by question id: a scale value or a comment."""
        record = enrollment.student_record
        if student is None or student.person_id is None or student.person_id != record.person_id:
            raise PermissionDenied
        if not self.tasks.is_open(enrollment):
            raise ValidationError({"evaluation": _("The course evaluation is not open for this course.")})
        already = _("You have already evaluated this course.")
        if EvaluationCompletion.objects.filter(enrollment_id=enrollment.pk).exists():
            raise ValidationError({"evaluation": already})

        term_evaluation = TermEvaluation.objects.select_related("form").get(term_id=enrollment.term_id)
        rows = self.validated(term_evaluation, answers)
        try:
            with session_context().system("evaluation:submit"), transaction.atomic():
                EvaluationCompletion.objects.create(
                    enrollment_id=enrollment.pk, completed_at=timezone.now().replace(microsecond=0)
                )
                response = EvaluationResponse.objects.create(
                    term_id=enrollment.term_id, section_id=enrollment.section_id, form_id=term_evaluation.form_id
                )
                EvaluationAnswer.objects.bulk_create([EvaluationAnswer(response=response, **row) for row in rows])
        except IntegrityError:
            raise ValidationError({"evaluation": already}) from None

    def validated(self, term_evaluation: TermEvaluation, answers: Mapping[Any, Any]) -> list[dict[str, Any]]:
        form = term_evaluation.form
        given = {str(key): value for key, value in answers.items()}
        rows: list[dict[str, Any]] = []
        missing = 0
        for question in form.ordered_questions():
            answer = given.get(str(question.pk))
            if isinstance(answer, str):
                answer = answer.strip()
            if answer is None or answer == "":
                missing += 1 if question.is_required else 0
                continue
            if question.question_type == QuestionType.SCALE:
                value = self._integer(answer)
                if value is None or value < 1 or value > form.scale_points:
                    raise ValidationError({"answers": _("An answer is not valid.")})
                rows.append({"question_id": question.pk, "value": value, "comment": None})
            else:
                rows.append({"question_id": question.pk, "value": None, "comment": str(answer)[:COMMENT_MAX]})

        if missing > 0:
            raise ValidationError(
                {"answers": _("Answer every required question (%(count)s missing).") % {"count": missing}}
            )
        values = [row["value"] for row in rows if row["value"] is not None]
        if self.settings.reject_uniform_answers and len(values) > 2 and len(set(values)) == 1:
            raise ValidationError({"answers": _("Every answer is the same. Please answer each question.")})
        return rows

    @staticmethod
    def _integer(answer: Any) -> int | None:
        if isinstance(answer, bool):
            return None
        if isinstance(answer, int):
            return answer
        text = str(answer)
        return int(text) if _INTEGER.match(text) else None
