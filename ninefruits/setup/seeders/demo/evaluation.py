"""Demo course evaluation (original ``DemoEvaluationSeeder``): last term evaluated by about seven
in ten students with the results published, and the current term's evaluation open now for
demonstration.

The original created each completion, response and answer with its own insert; here they are
built in memory and written with bulk inserts (answers are about 15 per response). Response ids
are random UUIDs drawn from the demo generator, so ``--seed`` reproduces the data."""

from __future__ import annotations

import uuid
from datetime import datetime, time, timedelta
from typing import Any

from django.utils import timezone

from ninefruits.core.targeting import TargetCriteria
from ninefruits.evaluation.enums import QuestionType
from ninefruits.evaluation.models import (
    EvaluationAnswer,
    EvaluationCompletion,
    EvaluationForm,
    EvaluationResponse,
    TermEvaluation,
)
from ninefruits.registration.enums import EnrollmentStatus
from ninefruits.registration.models import Enrollment
from ninefruits.setup.seeders.base import Seeder
from ninefruits.term.enums import TermStatus, TermWindowType
from ninefruits.term.models import Term, TermWindow

from .options import current_options

BATCH = 2000

COMMENTS = [
    "The examples in class helped a lot.",
    "Please upload the slides before class.",
    "과제 설명이 조금 더 자세했으면 좋겠습니다.",
    "수업이 체계적이어서 좋았습니다.",
    "More practice problems before the exam would help.",
]


class DemoEvaluationSeeder(Seeder):
    def run(self) -> None:
        form = EvaluationForm.objects.filter(code="STANDARD").first()
        past = Term.objects.filter(status=TermStatus.GRADES_CLOSED).order_by("-start_date").first()
        today = timezone.localdate()
        current = (
            Term.objects.filter(status=TermStatus.PUBLISHED, start_date__lte=today).order_by("-start_date").first()
        )
        if form is None or past is None or current is None or TermEvaluation.objects.exists():
            return

        for term in (past, current):
            TermEvaluation.objects.create(term=term, form=form, minimum_responses=3)

        self.responses(past, form)
        published = datetime.combine(
            past.end_date + timedelta(days=14), time(0), tzinfo=timezone.get_default_timezone()
        )
        TermEvaluation.objects.filter(term=past).update(results_published_at=published)

        now = timezone.now().replace(microsecond=0)
        TermWindow.objects.create(
            term=current,
            session=current.full_term_session(),
            window_type=TermWindowType.COURSE_EVALUATION,
            name={"en": "Demo course evaluation", "ko": "시연용 강의평가", "zh-hans": "演示课程评价"},
            opens_at=now - timedelta(days=1),
            closes_at=now + timedelta(days=14),
            eligibility=TargetCriteria.everyone(),
        )

    def responses(self, term: Term, form: EvaluationForm) -> None:
        rng = current_options().rng
        questions = form.ordered_questions()
        enrollments = (
            Enrollment.objects.filter(term=term, status=EnrollmentStatus.COMPLETED)
            .order_by("pk")
            .values_list("pk", "section_id")
        )
        zone = timezone.get_default_timezone()
        completions: list[EvaluationCompletion] = []
        responses: list[EvaluationResponse] = []
        answers: list[EvaluationAnswer] = []
        for enrollment_id, section_id in enrollments.iterator(chunk_size=BATCH):
            if rng.randint(1, 10) > 7:
                continue
            # Each section gets a tendency, so results differ between sections.
            center = 3 + (section_id % 3) * 0.5
            completed = datetime.combine(term.end_date - timedelta(days=rng.randint(1, 10)), time(0), tzinfo=zone)
            completions.append(EvaluationCompletion(enrollment_id=enrollment_id, completed_at=completed))
            response = EvaluationResponse(
                id=uuid.UUID(int=rng.getrandbits(128), version=4),
                term_id=term.pk,
                section_id=section_id,
                form_id=form.pk,
            )
            responses.append(response)
            for question in questions:
                if question.question_type == QuestionType.TEXT:
                    if rng.randint(1, 4) == 1:
                        answers.append(
                            EvaluationAnswer(response=response, question=question, comment=rng.choice(COMMENTS))
                        )
                    continue
                value = int(max(1, min(form.scale_points, _php_round(center + rng.randint(-15, 15) / 10))))
                answers.append(
                    EvaluationAnswer(
                        response=response,
                        question=question,
                        value=form.scale_points + 1 - value if question.is_reversed else value,
                    )
                )
            if len(answers) >= BATCH:
                self._flush(completions, responses, answers)
        self._flush(completions, responses, answers)

    @staticmethod
    def _flush(completions: list[Any], responses: list[Any], answers: list[Any]) -> None:
        EvaluationCompletion.objects.bulk_create(completions, batch_size=BATCH)
        EvaluationResponse.objects.bulk_create(responses, batch_size=BATCH)
        EvaluationAnswer.objects.bulk_create(answers, batch_size=BATCH)
        completions.clear()
        responses.clear()
        answers.clear()


def _php_round(value: float) -> int:
    """Half away from zero, as PHP ``round``."""
    return int(value + 0.5) if value >= 0 else -int(-value + 0.5)
