"""Query counts of the registration page (Phase 13 load test): the number of queries does not
grow with the student's registrations, waitlists or the search results."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import pytest
from django.db import connection
from django.test import Client
from django.test.utils import CaptureQueriesContext

from ninefruits.core.db import session_context
from ninefruits.registration.data import EnrollOptions
from ninefruits.registration.enums import AttemptOutcome
from ninefruits.term.enums import TermWindowType
from tests.factories.curriculum import CourseFactory

from .conftest import enroll, open_window, upcoming_term

pytestmark = pytest.mark.django_db

URL = "/portal/registration/"


def page_queries(client: Client, term: Any) -> tuple[int, str]:
    with CaptureQueriesContext(connection) as queries:
        response = client.get(URL, {"term": term.pk, "q": "LOAD"})
    assert response.status_code == 200
    return len(queries.captured_queries), response.content.decode()


def test_registration_page_queries_do_not_grow_with_rows(
    make_section: Callable[..., Any], make_student: Callable[..., tuple[Any, Any]]
) -> None:
    term = upcoming_term()
    open_window(term, TermWindowType.REGISTRATION)
    record, student = make_student()
    other, other_user = make_student()
    client = Client()
    client.force_login(student)
    session_context().reset()

    def add(index: int) -> None:
        """One more registration, one more waitlist entry and two more search results."""
        meeting = {"weekday": index, "start_time": "09:00", "end_time": "10:15"}
        taken = make_section(term, meeting=meeting, course=CourseFactory(code=f"LOADE{index}"))
        assert enroll(record, taken, student).outcome == AttemptOutcome.SUCCEEDED
        later = {"weekday": index, "start_time": "13:00", "end_time": "14:15"}
        full = make_section(
            term, capacity=1, waitlist_capacity=5, meeting=later, course=CourseFactory(code=f"LOADW{index}")
        )
        assert enroll(other, full, other_user).outcome == AttemptOutcome.SUCCEEDED
        waited = enroll(record, full, student, EnrollOptions(waitlist_if_full=True))
        assert waited.outcome == AttemptOutcome.WAITLISTED
        session_context().reset()

    add(1)
    page_queries(client, term)  # first request: one-time work (session, settings cache)
    one, page = page_queries(client, term)
    assert page.count("data-section=") == 2
    assert "Waitlist position 1" in page

    add(2)
    add(3)
    three, page = page_queries(client, term)
    assert page.count("data-section=") == 6
    assert page.count("data-waitlist") == 3

    assert three == one
