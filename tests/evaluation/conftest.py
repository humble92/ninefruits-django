"""Fixtures for the course evaluation tests (original ``beforeEach`` of
``tests/Feature/Evaluation/EvaluationTest.php``): a running term with a course evaluation window
open from yesterday for a week, a form with a scale question, a reversed one and an optional
comment, the term's evaluation (minimum 2 responses) and a published section with an instructor."""

from __future__ import annotations

from datetime import timedelta
from typing import Any

import pytest
from django.test import Client
from django.utils import timezone

from ninefruits.core.db import session_context
from ninefruits.evaluation.enums import QuestionType
from ninefruits.evaluation.models import TermEvaluation
from ninefruits.evaluation.settings import EvaluationSettings
from ninefruits.offering.models import SectionInstructor
from ninefruits.security.enums import MfaEnforcement
from ninefruits.settings.groups.security import SecuritySettings
from ninefruits.term.enums import TermWindowType
from tests.factories.evaluation import EvaluationFormFactory, EvaluationQuestionFactory
from tests.factories.offering import SectionFactory
from tests.factories.person import InstructorFactory, StudentRecordFactory
from tests.factories.registration import EnrollmentFactory
from tests.factories.security import UserFactory
from tests.factories.term import TermFactory, TermWindowFactory
from tests.reference_conftest import *  # noqa: F403


def now() -> Any:
    return timezone.now().replace(microsecond=0)


def running_term(**kwargs: Any) -> Any:
    """Original ``Term::factory()->published()->between(now()->subMonths(4), now()->addWeek())``."""
    today = timezone.localdate()
    return TermFactory(
        published=True, start_date=today - timedelta(days=120), end_date=today + timedelta(days=7), **kwargs
    )


def open_evaluation_window(term: Any) -> Any:
    """A course evaluation window of the full-term session from yesterday for a week."""
    return TermWindowFactory(
        term=term,
        window_type=TermWindowType.COURSE_EVALUATION,
        session=term.full_term_session(),
        opens_at=now() - timedelta(days=1),
        closes_at=now() + timedelta(weeks=1),
    )


def teacher_of(section: Any) -> Any:
    instructor = InstructorFactory()
    SectionInstructor.objects.create(section=section, instructor=instructor, role="primary")
    return UserFactory(person=instructor.person)


def set_evaluation(**values: Any) -> EvaluationSettings:
    settings = EvaluationSettings.load()
    for name, value in values.items():
        setattr(settings, name, value)
    settings.save()
    return settings


def signed_in(user: Any) -> Client:
    client = Client()
    client.force_login(user)
    session_context().reset()
    return client


@pytest.fixture(autouse=True)
def _mfa_not_used(request: pytest.FixtureRequest) -> None:
    if "db" not in request.fixturenames and request.node.get_closest_marker("django_db") is None:
        return
    request.getfixturevalue("db")
    settings = SecuritySettings.load()
    settings.mfa_enforcement = MfaEnforcement.DISABLED
    settings.save()


class World:
    """The original test's ``$this``."""

    def __init__(self, **values: Any) -> None:
        self.__dict__.update(values)

    def student(self, section: Any = None, **kwargs: Any) -> tuple[Any, Any]:
        """Original ``evaluatingStudent``: an enrollment in the section and the student's account."""
        record = StudentRecordFactory()
        enrollment = EnrollmentFactory(section=section or self.section, student_record=record, **kwargs)
        return enrollment, UserFactory(person=record.person)

    def answers(self, clear: int = 4, hard: int = 2, comment: str | None = None) -> dict[int, Any]:
        return {self.clear.pk: clear, self.hard.pk: hard, self.comment.pk: comment}


@pytest.fixture
def world(db: None) -> World:
    term = running_term()
    window = open_evaluation_window(term)
    form = EvaluationFormFactory(code="T", name={"en": "Test form"}, scale_points=5)
    clear = EvaluationQuestionFactory(form=form, sort_order=1, text={"en": "Clear"})
    hard = EvaluationQuestionFactory(form=form, sort_order=2, text={"en": "Too hard"}, is_reversed=True)
    comment = EvaluationQuestionFactory(
        form=form, sort_order=3, text={"en": "Comments"}, question_type=QuestionType.TEXT, is_required=False
    )
    evaluation = TermEvaluation.objects.create(term=term, form=form, minimum_responses=2)
    section = SectionFactory(term=term, published=True)
    teacher = teacher_of(section)
    return World(
        term=term,
        window=window,
        form=form,
        clear=clear,
        hard=hard,
        comment=comment,
        evaluation=evaluation,
        section=section,
        teacher=teacher,
    )


@pytest.fixture
def korean_scale(db: None) -> Any:
    """Original ``GradeScale::factory()->korean()->create()``: the 4.5 scale as the default."""
    from ninefruits.setup.seeders.profiles.korean_university import seed_scale_45

    return seed_scale_45(True)
