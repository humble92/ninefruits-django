"""Original tests/Feature/Person/AdditionalProgramTest.php."""

from __future__ import annotations

from collections.abc import Callable
from datetime import timedelta
from typing import Any

import pytest
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import connection
from django.utils import timezone

from ninefruits.core.db import session_context
from ninefruits.core.targeting import TargetCriteria
from ninefruits.person.actions import (
    CancelAdditionalProgramRequest,
    DecideAdditionalProgramRequest,
    EndAdditionalProgram,
    RequestAdditionalProgram,
)
from ninefruits.person.enums import AdditionalProgramRequestStatus, AdditionalProgramRole
from ninefruits.person.models import StudentRecord
from ninefruits.security.enums import Permission, ScopeType
from ninefruits.term.enums import TermWindowType
from tests.factories.organization import OrgUnitFactory, ProgramFactory
from tests.factories.person import StudentRecordFactory
from tests.factories.security import UserFactory
from tests.factories.term import TermFactory, TermWindowFactory

pytestmark = pytest.mark.django_db


@pytest.fixture
def world() -> dict[str, Any]:
    home = OrgUnitFactory(code="HOME")
    target = OrgUnitFactory(code="TGT")
    major = ProgramFactory(org_unit=home)
    second = ProgramFactory(org_unit=target, allows_second_major=True, allows_minor=True)
    closed = ProgramFactory(org_unit=target)
    record = StudentRecordFactory(program=major, year_level=2)
    today = timezone.localdate()
    term = TermFactory(published=True, start_date=today + timedelta(days=60), end_date=today + timedelta(days=180))
    TermWindowFactory(
        term=term,
        window_type=TermWindowType.ADDITIONAL_PROGRAM_APPLICATION,
        eligibility=TargetCriteria(year_levels=[2, 3]),
    )
    return {
        "home": home,
        "target": target,
        "major": major,
        "second": second,
        "closed": closed,
        "record": record,
        "student": UserFactory(person=record.person),
        "term": term,
        "approver": UserFactory(
            permissions=[Permission.ADDITIONAL_PROGRAMS_APPROVE],
            permissions__scope_type=ScopeType.ORG_UNIT,
            permissions__scope_id=target.pk,
        ),
    }


def request_errors(callback: Callable[[], Any]) -> list[str]:
    try:
        callback()
    except ValidationError as error:
        return list(error.message_dict)
    return []


def _request(
    world: dict[str, Any], program: Any, role: AdditionalProgramRole = AdditionalProgramRole.SECOND_MAJOR
) -> Any:
    record = StudentRecord.objects.get(pk=world["record"].pk)
    return RequestAdditionalProgram().handle(record, program, role, None, world["student"])


def test_takes_a_request_in_an_open_window_and_adds_the_program_on_approval_from_the_term_start(
    world: dict[str, Any],
) -> None:
    request = RequestAdditionalProgram().handle(
        world["record"], world["second"], AdditionalProgramRole.SECOND_MAJOR, "I like it", world["student"]
    )
    assert request.term_id == world["term"].pk
    assert request.org_unit_id == world["target"].pk

    program = DecideAdditionalProgramRequest().approve(request, world["approver"], "Welcome")

    request.refresh_from_db()
    assert program.start_date == world["term"].start_date
    assert request.status == AdditionalProgramRequestStatus.APPROVED
    assert world["second"].pk in world["record"].target_program_ids()
    assert world["target"].pk in world["record"].target_org_unit_ids()


def test_refuses_requests_outside_the_window_for_programs_that_do_not_accept_them_and_beyond_the_limit(
    world: dict[str, Any],
) -> None:
    assert request_errors(lambda: _request(world, world["closed"])) == ["program_id"]
    assert request_errors(lambda: _request(world, world["major"])) == ["program_id"]

    _request(world, world["second"])
    another = ProgramFactory(allows_second_major=True)
    assert request_errors(lambda: _request(world, another)) == ["role"]  # one second major at a time

    StudentRecord.objects.filter(pk=world["record"].pk).update(year_level=4)
    # The window is for years 2-3.
    assert request_errors(lambda: _request(world, another, AdditionalProgramRole.MINOR)) == ["program_id"]


def test_lets_only_the_target_program_decide_and_the_student_cancel_while_pending(world: dict[str, Any]) -> None:
    request = _request(world, world["second"], AdditionalProgramRole.MINOR)
    home_staff = UserFactory(
        permissions=[Permission.ADDITIONAL_PROGRAMS_APPROVE],
        permissions__scope_type=ScopeType.ORG_UNIT,
        permissions__scope_id=world["home"].pk,
    )

    with pytest.raises(PermissionDenied):
        DecideAdditionalProgramRequest().approve(request, home_staff)

    CancelAdditionalProgramRequest().handle(request, world["student"])
    request.refresh_from_db()
    assert request.status == AdditionalProgramRequestStatus.CANCELLED
    assert request_errors(lambda: DecideAdditionalProgramRequest().approve(request, world["approver"])) == ["status"]


def test_ends_a_second_major_and_allows_taking_it_up_again_later(world: dict[str, Any]) -> None:
    request = _request(world, world["second"])
    program = DecideAdditionalProgramRequest().approve(request, world["approver"])

    EndAdditionalProgram().handle(program, program.start_date + timedelta(days=150), "Gave it up", world["approver"])

    again = _request(world, world["second"])
    assert DecideAdditionalProgramRequest().approve(again, world["approver"]).end_date is None


def _exists(sql: str, pk: int) -> bool:
    with connection.cursor() as cursor:
        cursor.execute(sql, [pk])
        return cursor.fetchone() is not None


def test_shows_the_target_department_its_applicants_and_second_majors_in_both_layers(world: dict[str, Any]) -> None:
    request = _request(world, world["second"])
    record, approver = world["record"], world["approver"]
    target_viewer = UserFactory(
        permissions=[Permission.STUDENT_RECORDS_VIEW],
        permissions__scope_type=ScopeType.ORG_UNIT,
        permissions__scope_id=world["target"].pk,
    )
    context = session_context()
    context.use_baseline({})

    # Approver: sees the applicant's record while the request is pending.
    context.for_user(approver.pk)
    assert _exists("SELECT 1 FROM student_records WHERE id = %s", record.pk)
    assert _exists("SELECT 1 FROM additional_program_requests WHERE id = %s", request.pk)
    context.use_baseline({"app.actor": "system:test"})
    assert StudentRecord.objects.visible_to(approver).filter(pk=record.pk).exists()

    # Target department records staff: not before approval, yes after.
    context.use_baseline({})
    context.for_user(target_viewer.pk)
    assert not _exists("SELECT 1 FROM student_records WHERE id = %s", record.pk)
    context.use_baseline({"app.actor": "system:test"})
    assert not StudentRecord.objects.visible_to(target_viewer).filter(pk=record.pk).exists()

    DecideAdditionalProgramRequest().approve(request, approver)
    context.use_baseline({})
    context.for_user(target_viewer.pk)
    assert _exists("SELECT 1 FROM student_records WHERE id = %s", record.pk)
    context.use_baseline({"app.actor": "system:test"})
    assert StudentRecord.objects.visible_to(target_viewer).filter(pk=record.pk).exists()
