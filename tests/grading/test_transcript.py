"""The grade report (original ``TranscriptController``): finalized grades and W only, the retake
mark, the PDF through Gotenberg, staff access recorded as ``transcript.viewed``, hidden terms
(the Phase 7 hook), and the grade entry link on the teaching page."""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any

import httpx
import pytest
import respx
from django.conf import settings
from django.test import Client

from ninefruits.audit.models import ActivityLog
from ninefruits.core.db import session_context
from ninefruits.grading.services import TermRecordCalculator, register_hidden_terms, unregister_hidden_terms
from ninefruits.registration.enums import EnrollmentStatus
from ninefruits.security.enums import Permission
from tests.factories.offering import SectionFactory
from tests.factories.person import StudentRecordFactory
from tests.factories.registration import EnrollmentFactory
from tests.factories.security import UserFactory

from .conftest import teacher_of, term_between

pytestmark = pytest.mark.django_db

CONVERT = f"{settings.GOTENBERG_URL.rstrip('/')}/forms/chromium/convert/html"


@pytest.fixture
def student(korean_scale: Any) -> dict[str, Any]:
    record = StudentRecordFactory()
    spring = term_between("2025-03-01", "2025-06-20")
    fall = term_between("2025-09-01", "2025-12-20")
    first = EnrollmentFactory(student_record=record, section=SectionFactory(term=spring, published=True), grade="D0")
    retake = EnrollmentFactory(
        student_record=record,
        section=SectionFactory(term=fall, published=True, course=first.course),
        grade="A0",
        repeats_enrollment=first,
        is_retake=True,
    )
    withdrawn = EnrollmentFactory(
        student_record=record, section=SectionFactory(term=fall, published=True), status=EnrollmentStatus.WITHDRAWN
    )
    draft = EnrollmentFactory(student_record=record, section=SectionFactory(term=fall, published=True))
    TermRecordCalculator().recalculate(record)
    return {
        "record": record,
        "user": UserFactory(person=record.person),
        "first": first,
        "retake": retake,
        "withdrawn": withdrawn,
        "draft": draft,
        "spring": spring,
        "fall": fall,
    }


def signed_in(user: Any) -> Client:
    client = Client()
    client.force_login(user)
    session_context().reset()
    return client


def test_shows_final_grades_and_withdrawals_with_the_replaced_attempt(student: dict[str, Any]) -> None:
    page = signed_in(student["user"]).get("/portal/grades/transcript/").content.decode()
    assert student["first"].course.code in page
    assert student["withdrawn"].course.code in page
    assert student["draft"].course.code not in page
    assert "replaced by a retake in the cumulative GPA" in page
    assert ">W<" in page
    # Cumulative GPA with the retake only: A0 = 4.00.
    assert "4.00" in page


@respx.mock
def test_renders_the_report_as_a_pdf(student: dict[str, Any]) -> None:
    route = respx.post(CONVERT).mock(return_value=httpx.Response(200, content=b"%PDF-1.7 fake"))
    response = signed_in(student["user"]).get("/portal/grades/transcript/", {"format": "pdf"})
    assert response.status_code == 200
    assert response["Content-Type"] == "application/pdf"
    assert response.content == b"%PDF-1.7 fake"
    assert route.called


def test_staff_open_records_they_can_see_and_the_view_is_recorded(student: dict[str, Any]) -> None:
    record = student["record"]
    staff = UserFactory(permissions=[Permission.GRADES_VIEW, Permission.STUDENT_RECORDS_VIEW])
    assert signed_in(staff).get(f"/student-records/{record.pk}/transcript/").status_code == 200
    entry = ActivityLog.objects.get(event="transcript.viewed")
    assert entry.properties == {"student_number": record.student_number}

    assert signed_in(UserFactory(permissions=[Permission.GRADES_VIEW])).get(
        f"/student-records/{record.pk}/transcript/"
    ).status_code in (403, 404)


@pytest.fixture
def hidden_fall(student: dict[str, Any]) -> Iterator[None]:
    register_hidden_terms(
        "test",
        lambda record: [student["fall"].pk],
        notice=lambda term: f"Hidden until the evaluation of {term.code}",
    )
    yield
    unregister_hidden_terms("test")


def test_hides_terms_a_provider_names(student: dict[str, Any], hidden_fall: None) -> None:
    client = signed_in(student["user"])
    page = client.get("/portal/grades/").content.decode()
    assert f"Hidden until the evaluation of {student['fall'].code}" in page
    assert student["withdrawn"].course.code not in page
    assert student["first"].course.code in page


def test_links_grade_entry_from_the_teaching_page(korean_scale: Any) -> None:
    section = SectionFactory(published=True)
    teacher = teacher_of(section)
    page = signed_in(teacher).get("/portal/teaching/", {"term": section.term_id}).content.decode()
    assert f"/portal/sections/{section.pk}/grades/" in page
