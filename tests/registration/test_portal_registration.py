"""The student registration page (original ``tests/Feature/Registration/PortalRegistrationTest.php``,
Livewire ``Registration``). Requests run as the signed-in student, so row level security applies
to every action."""

from __future__ import annotations

from typing import Any

import pytest
from django.test import Client

from ninefruits.core.db import session_context
from ninefruits.offering.actions import SaveSectionMeeting
from ninefruits.registration.actions import EnrollStudent
from ninefruits.registration.enums import EnrollmentStatus, WaitlistStatus
from ninefruits.registration.models import CartItem, CreditLimitPolicy, Enrollment, WaitlistEntry
from ninefruits.security.enums import Permission
from ninefruits.term.enums import TermWindowType
from tests.factories.facility import RoomFactory
from tests.factories.offering import SectionFactory
from tests.factories.person import StudentRecordFactory
from tests.factories.security import UserFactory

from .conftest import open_window, upcoming_term

pytestmark = pytest.mark.django_db

URL = "/portal/registration/"


@pytest.fixture
def setup(db: None) -> dict[str, Any]:
    term = upcoming_term()
    open_window(term, TermWindowType.REGISTRATION)
    CreditLimitPolicy.objects.create(name={"en": "Standard"}, max_credits=18)
    planner = UserFactory(permissions=[Permission.SECTIONS_MANAGE])
    section = SectionFactory(term=term, published=True, capacity=1, waitlist_capacity=3)
    SaveSectionMeeting()(
        section, {"weekday": 2, "start_time": "10:30", "end_time": "11:45", "room_id": RoomFactory().pk}, planner
    )
    record = StudentRecordFactory()
    student = UserFactory(person=record.person)
    client = Client()
    client.force_login(student)
    session_context().reset()  # the login listener set the student's database context
    return {"term": term, "section": section, "record": record, "student": student, "client": client}


def act(client: Client, term: Any, action: str, **fields: Any) -> str:
    response = client.post(URL, {"action": action, "term": term.pk, **fields}, follow=True)
    assert response.status_code == 200
    return response.content.decode()


def test_finds_a_section_registers_and_drops_it(setup: dict[str, Any]) -> None:
    client, term, section = setup["client"], setup["term"], setup["section"]

    page = client.get(URL).content.decode()
    assert f'value="{term.pk}" selected' in page
    assert "Open" in page
    page = client.get(URL, {"term": term.pk, "q": section.course.code}).content.decode()
    assert section.label() in page

    page = act(client, term, "enroll", section_id=section.pk)
    assert 'data-tone="success"' in page

    enrollment = Enrollment.objects.get(student_record=setup["record"])
    assert "My registrations" in page
    assert f"{int(enrollment.credits)} / 18" in page

    page = act(client, term, "drop", enrollment_id=enrollment.pk)
    assert 'data-tone="success"' in page
    enrollment.refresh_from_db()
    assert enrollment.status == EnrollmentStatus.DROPPED


def test_registers_the_cart_and_reports_each_section(setup: dict[str, Any]) -> None:
    client, term, section = setup["client"], setup["term"], setup["section"]

    assert "Added to the cart." in act(client, term, "add_to_cart", section_id=section.pk)
    assert f"{section.label()}: Registered." in act(client, term, "submit_cart")

    assert Enrollment.objects.filter(student_record=setup["record"]).count() == 1
    assert CartItem.objects.count() == 0


def test_joins_and_leaves_the_waitlist_of_a_full_section(setup: dict[str, Any]) -> None:
    client, term, section = setup["client"], setup["term"], setup["section"]
    other = StudentRecordFactory()
    EnrollStudent().handle(other, section, UserFactory(person=other.person))

    page = client.get(URL, {"term": term.pk, "q": section.course.code}).content.decode()
    assert "Join waitlist" in page
    assert 'data-tone="error"' in act(client, term, "enroll", section_id=section.pk)
    page = act(client, term, "waitlist", section_id=section.pk)
    assert 'data-tone="info"' in page
    assert "Waitlist position 1" in page

    entry = WaitlistEntry.objects.get(student_record=setup["record"])
    act(client, term, "leave_waitlist", entry_id=entry.pk)
    entry.refresh_from_db()
    assert entry.status == WaitlistStatus.REMOVED


def test_does_not_act_on_another_students_registration(setup: dict[str, Any]) -> None:
    other = StudentRecordFactory()
    enrollment = EnrollStudent().handle(other, setup["section"], UserFactory(person=other.person)).enrollment

    response = setup["client"].post(URL, {"action": "drop", "term": setup["term"].pk, "enrollment_id": enrollment.pk})
    assert response.status_code == 404
    enrollment.refresh_from_db()
    assert enrollment.status == EnrollmentStatus.ENROLLED


def test_shows_the_student_timetable_and_reloads_search_results_with_htmx(setup: dict[str, Any]) -> None:
    client, term, section = setup["client"], setup["term"], setup["section"]
    act(client, term, "enroll", section_id=section.pk)

    page = client.get(URL, {"term": term.pk}).content.decode()
    assert "data-timetable-list" in page
    assert section.label() in page

    partial = client.get(URL, {"term": term.pk, "q": section.course.code, "partial": "results"}, HTTP_HX_REQUEST="true")
    body = partial.content.decode()
    assert 'id="registration-results"' in body
    assert "<header" not in body


def test_limits_registration_actions_per_user(setup: dict[str, Any], monkeypatch: pytest.MonkeyPatch) -> None:
    import time
    from types import SimpleNamespace

    from django.core.cache import cache
    from django_ratelimit import core

    cache.clear()
    # One fixed moment: the limit counts per minute window, the test must not cross one.
    moment = time.time()
    monkeypatch.setattr(core, "time", SimpleNamespace(time=lambda: moment))
    client, term, section = setup["client"], setup["term"], setup["section"]
    for _ in range(30):
        client.post(URL, {"action": "add_to_cart", "term": term.pk, "section_id": section.pk})
    page = act(client, term, "add_to_cart", section_id=section.pk)
    assert "Too many requests. Wait a minute and try again." in page
