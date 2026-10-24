"""Registration commands (original ``tests/Feature/Registration/RegistrationCommandsTest.php``):
``registration_preflight``, ``registration_simulate``, ``waitlist_promote``,
``registration_release_reserved_seats``."""

from __future__ import annotations

import io
from datetime import timedelta
from typing import Any

import pytest
from django.core.management import call_command

from ninefruits.audit.models import ActivityLog
from ninefruits.core.targeting import TargetCriteria
from ninefruits.offering.models import SectionSeatGroup
from ninefruits.registration import tasks
from ninefruits.registration.actions import EnrollStudent
from ninefruits.registration.enums import WaitlistStatus
from ninefruits.registration.models import CreditLimitPolicy, RegistrationAttempt, WaitlistEntry
from tests.factories.offering import SectionFactory
from tests.factories.person import StudentRecordFactory
from tests.factories.security import UserFactory

from .conftest import now, open_registration, upcoming_term

pytestmark = pytest.mark.django_db


@pytest.fixture
def setup(db: None) -> dict[str, Any]:
    term = upcoming_term()
    section = SectionFactory(term=term, published=True, capacity=1, waitlist_capacity=2)
    return {"term": term, "section": section, "record": StudentRecordFactory()}


def run(*args: Any, **options: Any) -> tuple[int, str]:
    out, err = io.StringIO(), io.StringIO()
    code = call_command(*args, stdout=out, stderr=err, **options)
    return int(code or 0), out.getvalue() + err.getvalue()


def test_reports_missing_windows_and_credit_limits_before_registration_opens(setup: dict[str, Any]) -> None:
    code, output = run("registration_preflight", setup["term"].code)
    assert code == 2
    assert "No registration window." in output
    assert "match no credit limit policy" in output

    open_registration(setup["term"])
    CreditLimitPolicy.objects.create(name={"en": "Standard"}, max_credits=18, eligibility=TargetCriteria.everyone())

    code, output = run("registration_preflight", setup["term"].code)
    assert code == 0
    assert "No rule set" in output
    assert run("registration_preflight", "NOPE")[0] == 1


def test_simulates_a_registration_without_changing_anything(setup: dict[str, Any]) -> None:
    label = setup["section"].label()
    number = setup["record"].student_number

    code, output = run("registration_simulate", number, label)
    assert code == 2
    assert "Registration is not open for you now." in output

    open_registration(setup["term"])

    code, output = run("registration_simulate", number, label)
    assert code == 0
    assert "Would be registered." in output
    setup["section"].refresh_from_db()
    assert setup["section"].enrolled_count == 0
    assert RegistrationAttempt.objects.count() == 0


def test_promotes_waiting_students_when_a_seat_is_free(setup: dict[str, Any], mailoutbox: list[Any]) -> None:
    open_registration(setup["term"])
    section = setup["section"]
    EnrollStudent().handle(StudentRecordFactory(), section, None)
    entry = WaitlistEntry.objects.create(section=section, student_record=setup["record"], requested_at=now())
    section.refresh_from_db()
    section.capacity = 2
    section.save()
    actor = UserFactory()

    code, output = run("waitlist_promote", setup["term"].code, actor=actor.email)

    assert code == 0
    assert "1 section(s): 1 promoted, 0 removed, 0 expired." in output
    entry.refresh_from_db()
    assert entry.status == WaitlistStatus.PROMOTED
    assert ActivityLog.objects.filter(event="command.executed", properties__command="waitlist_promote").exists()


def test_hands_released_reserved_seats_to_the_waitlist_once(
    setup: dict[str, Any], monkeypatch: pytest.MonkeyPatch, django_capture_on_commit_callbacks: Any
) -> None:
    dispatched: list[int] = []
    monkeypatch.setattr(tasks.promote_waitlist, "delay", lambda section_id: dispatched.append(section_id))
    SectionSeatGroup.objects.create(
        section=setup["section"], name={"en": "Majors"}, capacity=1, releases_at=now() - timedelta(minutes=1)
    )

    with django_capture_on_commit_callbacks(execute=True):
        assert "1 section(s)" in run("registration_release_reserved_seats")[1]
    with django_capture_on_commit_callbacks(execute=True):
        assert "0 section(s)" in run("registration_release_reserved_seats")[1]

    assert dispatched == [setup["section"].pk]
