"""Course evaluation on the tiny demo (original Phase 7 datasets of
``tests/Feature/Admin/AdminPagesTest.php`` and the ``DemoEvaluationSeeder`` result in the phase
report): last term evaluated and published, the current term's evaluation open; every evaluation
page for staff, the instructor's results and the student's evaluations."""

from __future__ import annotations

from collections.abc import Iterator

import pytest

from ninefruits.evaluation.models import (
    EvaluationAnswer,
    EvaluationCompletion,
    EvaluationResponse,
    SectionEvaluation,
    TermEvaluation,
)
from ninefruits.evaluation.services import EvaluationResults
from ninefruits.security.enums import Permission
from ninefruits.security.models import User
from ninefruits.setup.seeders.demo import DemoOptions, use_options
from ninefruits.setup.seeders.demo.accounts import DemoAccountSeeder
from ninefruits.setup.seeders.demo.curriculum import DemoCurriculumSeeder
from ninefruits.setup.seeders.demo.evaluation import DemoEvaluationSeeder
from ninefruits.setup.seeders.demo.grading import DemoGradeHistorySeeder, DemoGradingSeeder
from ninefruits.setup.seeders.demo.people import DemoPeopleSeeder
from ninefruits.setup.seeders.demo.reference import DemoReferenceSeeder
from ninefruits.setup.seeders.demo.registration import DemoRegistrationSeeder
from ninefruits.term.enums import TermWindowType
from ninefruits.term.models import TermWindow
from tests.factories.security import UserFactory

from .conftest import signed_in

pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def demo(essential_data: None) -> Iterator[None]:
    with use_options(DemoOptions(size="tiny", seed=42)):
        for seeder in (
            DemoAccountSeeder,
            DemoReferenceSeeder,
            DemoPeopleSeeder,
            DemoCurriculumSeeder,
            DemoGradeHistorySeeder,
            DemoRegistrationSeeder,
            DemoGradingSeeder,
            DemoEvaluationSeeder,
        ):
            seeder()()
    yield


def test_seeds_published_past_responses_and_an_open_current_evaluation() -> None:
    past, current = list(TermEvaluation.objects.select_related("term").order_by("term__start_date"))
    assert past.results_published_at is not None
    assert current.results_published_at is None
    assert EvaluationResponse.objects.filter(term=past.term).count() == EvaluationCompletion.objects.count() > 0
    assert EvaluationAnswer.objects.filter(comment__isnull=False).exists()
    assert TermWindow.objects.filter(
        term=current.term, window_type=TermWindowType.COURSE_EVALUATION, name__isnull=False
    ).exists()
    # Some sections reach the minimum (3 responses) and show results.
    shown = [
        section
        for section in SectionEvaluation.objects.filter(term=past.term)
        if EvaluationResults().for_section(section).shown
    ]
    assert shown

    # Running it again changes nothing.
    responses = EvaluationResponse.objects.count()
    with use_options(DemoOptions(size="tiny", seed=42)):
        DemoEvaluationSeeder()()
    assert EvaluationResponse.objects.count() == responses


def test_renders_the_evaluation_pages_on_the_demo() -> None:
    past = TermEvaluation.objects.order_by("term__start_date").first()
    section = SectionEvaluation.objects.filter(term=past.term, evaluation_responses__isnull=False).first()
    manager = UserFactory(permissions=list(Permission))
    client = signed_in(manager)
    pages = [
        "/admin/evaluation/termevaluation/",
        "/admin/evaluation/evaluationform/",
        f"/admin/evaluation/evaluationform/{past.form_id}/change/",
        "/admin/evaluation/sectionevaluation/",
        f"/admin/evaluation/sectionevaluation/?term={past.term_id}",
        "/admin/settings/evaluation/",
        f"/portal/sections/{section.pk}/evaluation/",
    ]
    for page in pages:
        assert client.get(page).status_code == 200, page

    academic_affairs = User.objects.get(email="academic-affairs@demo.test")
    assert signed_in(academic_affairs).get("/admin/evaluation/termevaluation/").status_code == 200


def test_shows_the_instructor_results_and_the_students_evaluations() -> None:
    instructor = User.objects.get(email="instructor@demo.test")
    past = TermEvaluation.objects.order_by("term__start_date").first()
    client = signed_in(instructor)
    page = client.get(f"/portal/teaching/?term={past.term_id}").content.decode()
    assert "Course evaluation results" in page
    taught = SectionEvaluation.objects.taught_by(instructor.person_id).filter(term=past.term)
    for section in taught:
        assert client.get(f"/portal/sections/{section.pk}/evaluation/").status_code == 200

    student = User.objects.get(email="student@demo.test")
    assert signed_in(student).get("/portal/evaluations/").status_code == 200
