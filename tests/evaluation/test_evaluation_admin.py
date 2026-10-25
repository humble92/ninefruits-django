"""Course evaluation admin screens and commands (original
``tests/Feature/Evaluation/EvaluationAdminTest.php``): setting up a term, rendering every
evaluation page and publishing; a form with responses keeps its questions and is copied; reminders
and publication by command. Also the settings page and the standard form of the profile."""

from __future__ import annotations

import io
from typing import Any

import pytest
from django.core.management import call_command

from ninefruits.evaluation.models import EvaluationForm, EvaluationResponse, TermEvaluation
from ninefruits.evaluation.settings import EvaluationSettings
from ninefruits.security.enums import Permission
from ninefruits.security.models import User
from tests.factories.offering import SectionFactory
from tests.factories.person import StudentRecordFactory
from tests.factories.registration import EnrollmentFactory
from tests.factories.security import UserFactory

from .conftest import open_evaluation_window, running_term, signed_in

pytestmark = pytest.mark.django_db


@pytest.fixture
def setup(essential_data: None) -> dict[str, Any]:
    from ninefruits.setup.seeders.profiles.korean_university import KoreanUniversityProfileSeeder

    KoreanUniversityProfileSeeder()()
    return {
        "manager": UserFactory(permissions=list(Permission)),
        "form": EvaluationForm.objects.get(code="STANDARD"),
        "term": running_term(),
    }


def run(*args: Any, **options: Any) -> tuple[int, str]:
    out, err = io.StringIO(), io.StringIO()
    code = call_command(*args, stdout=out, stderr=err, **options)
    return int(code or 0), out.getvalue() + err.getvalue()


def test_seeds_the_standard_form_once_and_keeps_edits(setup: dict[str, Any]) -> None:
    from ninefruits.setup.seeders.profiles.korean_university import KoreanUniversityProfileSeeder

    form = setup["form"]
    assert form.questions.count() == 16
    assert form.questions.filter(is_reversed=True).count() == 1
    assert form.questions.filter(question_type="text", is_required=False).count() == 1
    assert form.name_translations["ko"] == "표준 강의평가"

    form.name = {"en": "Our evaluation"}
    form.save()
    KoreanUniversityProfileSeeder()()
    assert EvaluationForm.objects.count() == 1
    assert EvaluationForm.objects.get().name_translations == {"en": "Our evaluation"}
    assert EvaluationForm.objects.get().questions.count() == 16


def test_sets_up_a_term_renders_the_evaluation_pages_and_publishes(setup: dict[str, Any]) -> None:
    manager, form, term = setup["manager"], setup["form"], setup["term"]
    client = signed_in(manager)

    assert client.get("/admin/evaluation/termevaluation/prepare/").status_code == 200
    response = client.post(
        "/admin/evaluation/termevaluation/prepare/",
        {"term_id": term.pk, "evaluation_form_id": form.pk, "minimum_responses": 4, "minimum_response_percent": ""},
    )
    assert response.status_code == 302
    evaluation = TermEvaluation.objects.get()
    assert (evaluation.minimum_responses, evaluation.minimum_response_percent) == (4, 25)

    section = SectionFactory(term=term, published=True)
    pages = [
        "/admin/evaluation/termevaluation/",
        f"/admin/evaluation/termevaluation/{evaluation.pk}/change/",
        f"/admin/evaluation/termevaluation/{evaluation.pk}/publish/",
        "/admin/evaluation/evaluationform/",
        "/admin/evaluation/evaluationform/add/",
        f"/admin/evaluation/evaluationform/{form.pk}/change/",
        f"/admin/evaluation/evaluationform/{form.pk}/copy/",
        "/admin/evaluation/sectionevaluation/",
        "/admin/evaluation/sectionevaluation/?term=all",
        "/admin/settings/evaluation/",
        f"/portal/sections/{section.pk}/evaluation/",
    ]
    for page in pages:
        assert client.get(page).status_code == 200, page
    assert client.get(f"/admin/evaluation/sectionevaluation/{section.pk}/results/").status_code == 302

    # Changing keeps the minimum response rate when left empty.
    client.post(
        f"/admin/evaluation/termevaluation/{evaluation.pk}/change/",
        {"evaluation_form_id": form.pk, "minimum_responses": 6, "minimum_response_percent": ""},
    )
    evaluation.refresh_from_db()
    assert (evaluation.minimum_responses, evaluation.minimum_response_percent) == (6, 25)

    assert client.post(f"/admin/evaluation/termevaluation/{evaluation.pk}/publish/", {}).status_code == 302
    evaluation.refresh_from_db()
    assert evaluation.results_published_at is not None
    assert evaluation.published_by_id == manager.pk


def test_refuses_another_form_once_the_term_has_responses(setup: dict[str, Any]) -> None:
    manager, form, term = setup["manager"], setup["form"], setup["term"]
    evaluation = TermEvaluation.objects.create(term=term, form=form)
    other = EvaluationForm.objects.create(code="OTHER", name={"en": "Other"})
    EvaluationResponse.objects.create(term=term, section=SectionFactory(term=term), form=form)

    response = signed_in(manager).post(
        f"/admin/evaluation/termevaluation/{evaluation.pk}/change/",
        {"evaluation_form_id": other.pk, "minimum_responses": "", "minimum_response_percent": ""},
        follow=True,
    )
    assert "The term already has responses with its form." in response.content.decode()
    evaluation.refresh_from_db()
    assert evaluation.form_id == form.pk


def test_locks_the_questions_of_a_form_with_responses_and_copies_it(setup: dict[str, Any]) -> None:
    manager, form, term = setup["manager"], setup["form"], setup["term"]
    TermEvaluation.objects.create(term=term, form=form)
    EvaluationResponse.objects.create(term=term, section=SectionFactory(term=term), form=form)
    client = signed_in(manager)

    assert form.is_locked() is True
    page = client.get(f"/admin/evaluation/evaluationform/{form.pk}/change/").content.decode()
    # Read only: no inputs for the questions, the scale cannot change.
    assert 'name="questions-0-sort_order"' not in page
    assert 'name="scale_points"' not in page or "disabled" in page

    response = client.post(f"/admin/evaluation/evaluationform/{form.pk}/copy/", {"code": "STANDARD2"})
    assert response.status_code == 302
    copy = EvaluationForm.objects.get(code="STANDARD2")
    assert copy.questions.count() == form.questions.count()
    assert copy.is_locked() is False
    assert copy.name_translations == form.name_translations
    page = client.get(f"/admin/evaluation/evaluationform/{copy.pk}/change/").content.decode()
    assert 'name="questions-0-sort_order"' in page

    # The code must be new and use letters, digits, dashes and underscores.
    assert client.post(f"/admin/evaluation/evaluationform/{form.pk}/copy/", {"code": "STANDARD2"}).status_code == 200
    assert client.post(f"/admin/evaluation/evaluationform/{form.pk}/copy/", {"code": "A B"}).status_code == 200
    assert EvaluationForm.objects.count() == 2


def test_reminds_students_with_open_evaluations_and_publishes_results_by_command(
    setup: dict[str, Any], mailoutbox: list[Any]
) -> None:
    form, term = setup["form"], setup["term"]
    TermEvaluation.objects.create(term=term, form=form)
    open_evaluation_window(term)
    record = StudentRecordFactory()
    EnrollmentFactory(section=SectionFactory(term=term, published=True), student_record=record)
    student = UserFactory(person=record.person)

    code, output = run("evaluation_remind", term.code, dry_run=True)
    assert code == 0
    assert "1 student(s) with evaluations to do, 0 reminder(s) sent." in output
    assert mailoutbox == []
    code, output = run("evaluation_remind", term.code)
    assert code == 0
    assert "1 reminder(s) sent." in output
    assert [message.to for message in mailoutbox] == [[student.email]]
    assert "anonymous" in mailoutbox[0].body
    assert run("evaluation_remind", "NOPE")[0] == 1

    assert run("evaluation_publish_results", "NOPE")[0] == 1
    code, output = run("evaluation_publish_results", term.code)
    assert code == 0
    assert "Published" in output
    assert TermEvaluation.objects.get().results_published_at is not None
    assert "Already published." in run("evaluation_publish_results", term.code)[1]


def test_saves_the_evaluation_settings(setup: dict[str, Any]) -> None:
    client = signed_in(setup["manager"])
    response = client.post(
        "/admin/settings/evaluation/",
        {
            "grades_require_evaluation": "",
            "reject_uniform_answers": "on",
            "minimum_responses": 7,
            "minimum_response_percent": 30,
        },
    )
    assert response.status_code == 302
    settings = EvaluationSettings.load()
    assert settings.grades_require_evaluation is False
    assert settings.reject_uniform_answers is True
    assert (settings.minimum_responses, settings.minimum_response_percent) == (7, 30)

    # Without evaluations.manage: no page.
    viewer = UserFactory(permissions=[Permission.EVALUATIONS_VIEW])
    assert signed_in(viewer).get("/admin/settings/evaluation/").status_code == 403


def test_renders_the_evaluation_pages_in_korean(setup: dict[str, Any]) -> None:
    manager: User = setup["manager"]
    manager.locale = "ko"
    manager.save(update_fields=["locale"])
    client = signed_in(manager)
    assert "학기 강의평가" in client.get("/admin/evaluation/termevaluation/").content.decode()
    assert "강의평가 양식" in client.get("/admin/evaluation/evaluationform/").content.decode()
    assert "강좌별 응답" in client.get("/admin/evaluation/sectionevaluation/").content.decode()
