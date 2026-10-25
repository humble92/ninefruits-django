"""Registration actions (original ``tests/Feature/Registration/EnrollmentTest.php``): snapshots and
seat counter, every reason at once, equivalent prerequisites, reserved seats, waitlist promotion
with the rules checked again, staff waivers and overrides, drop windows."""

from __future__ import annotations

from datetime import timedelta
from decimal import Decimal
from typing import Any

import pytest
from django.core.exceptions import ValidationError

from ninefruits.core.targeting import TargetCriteria
from ninefruits.curriculum.enums import RequisiteKind
from ninefruits.curriculum.models import CourseEquivalency, CourseRequisite
from ninefruits.offering.models import SectionSeatGroup
from ninefruits.registration.actions import DropEnrollment, ManageHolds
from ninefruits.registration.data import EnrollOptions
from ninefruits.registration.enums import AttemptOutcome, EnrollmentStatus, HoldType, RuleCode, WaitlistStatus
from ninefruits.registration.models import CreditLimitPolicy, Enrollment, RegistrationAttempt, WaitlistEntry
from ninefruits.security.enums import Permission
from ninefruits.term.models import TermWindow
from tests.factories.curriculum import CourseFactory
from tests.factories.offering import SectionFactory
from tests.factories.organization import ProgramFactory
from tests.factories.registration import EnrollmentFactory
from tests.factories.security import UserFactory

from .conftest import enroll, now, open_registration, upcoming_term

pytestmark = pytest.mark.django_db


@pytest.fixture
def setup(db: None) -> dict[str, Any]:
    term = upcoming_term()
    open_registration(term)
    CreditLimitPolicy.objects.create(name={"en": "Standard"}, max_credits=9)
    return {
        "term": term,
        "program": ProgramFactory(),
        "staff": UserFactory(permissions=[Permission.REGISTRATION_MANAGE, Permission.REGISTRATION_HOLDS_MANAGE]),
    }


def test_enrolls_with_a_snapshot_of_the_course_counts_the_seat_and_logs_the_attempt(
    setup: dict[str, Any], make_student: Any, make_section: Any
) -> None:
    record, user = make_student(setup["program"])
    section = make_section(setup["term"])

    outcome = enroll(record, section, user)

    assert outcome.outcome == AttemptOutcome.SUCCEEDED
    assert outcome.enrollment.credits == section.version.credits
    assert outcome.enrollment.version_id == section.version_id
    section.refresh_from_db()
    assert section.enrolled_count == 1
    assert RegistrationAttempt.objects.get(student_record=record).outcome == AttemptOutcome.SUCCEEDED


def test_reports_every_reason_at_once_when_refusing(
    setup: dict[str, Any], make_student: Any, make_section: Any
) -> None:
    record, user = make_student(setup["program"])
    ManageHolds().place(record, HoldType.UNREGISTERED, "Fee unpaid", setup["staff"])
    first = make_section(setup["term"])
    EnrollmentFactory(section=first, student_record=record, credits=Decimal(8))
    prerequisite = CourseFactory()
    second = make_section(setup["term"], meeting={"weekday": 1, "start_time": "10:00", "end_time": "11:00"})
    CourseRequisite.objects.create(
        course_version_id=second.version_id, kind=RequisiteKind.PREREQUISITE, required_course=prerequisite
    )

    outcome = enroll(record, second, user)
    failed = {result.code for result in outcome.evaluation.results if result.blocks()}

    assert outcome.outcome == AttemptOutcome.REFUSED
    assert failed == {RuleCode.HOLD, RuleCode.TIME_CONFLICT, RuleCode.CREDIT_LIMIT, RuleCode.REQUISITES}
    second.refresh_from_db()
    assert second.enrolled_count == 0


def test_counts_an_equivalent_course_as_the_prerequisite(
    setup: dict[str, Any], make_student: Any, make_section: Any
) -> None:
    record, user = make_student(setup["program"])
    old, new = CourseFactory(), CourseFactory()
    CourseEquivalency.objects.create(course=new, equivalent_course=old, effective_start_date="2000-01-01")
    earlier = SectionFactory(course=old, published=True)
    EnrollmentFactory(section=earlier, student_record=record, grade="B0")
    section = make_section(setup["term"])
    CourseRequisite.objects.create(
        course_version_id=section.version_id, kind=RequisiteKind.PREREQUISITE, required_course=new, minimum_grade=None
    )

    assert enroll(record, section, user).succeeded()


def test_keeps_reserved_seats_for_their_students_until_released(
    setup: dict[str, Any], make_student: Any, make_section: Any
) -> None:
    section = make_section(setup["term"], capacity=2)
    SectionSeatGroup.objects.create(
        section=section,
        name={"en": "Majors"},
        capacity=1,
        eligibility=TargetCriteria(program_ids=(setup["program"].pk,)),
        releases_at=now() + timedelta(days=1),
    )
    other = ProgramFactory()
    outsider1, user1 = make_student(other)
    outsider2, user2 = make_student(other)
    major, major_user = make_student(setup["program"])

    assert enroll(outsider1, section, user1).succeeded()
    assert enroll(outsider2, section, user2).refused_for_seat()
    assert enroll(major, section, major_user).enrollment.seat_group_id is not None


def test_promotes_the_waitlist_in_order_checking_every_rule_again(
    setup: dict[str, Any],
    make_student: Any,
    make_section: Any,
    mailoutbox: list[Any],
    django_capture_on_commit_callbacks: Any,
) -> None:
    section = make_section(setup["term"], capacity=1)
    section.waitlist_capacity = 5
    section.save()
    holder, holder_user = make_student(setup["program"])
    conflicted, conflicted_user = make_student(setup["program"])
    following, following_user = make_student(setup["program"])

    enroll(holder, section, holder_user)
    waitlisted = enroll(conflicted, section, conflicted_user, EnrollOptions(waitlist_if_full=True))
    assert waitlisted.outcome == AttemptOutcome.WAITLISTED
    WaitlistEntry.objects.filter(pk=waitlisted.waitlist_entry.pk).update(requested_at=now() - timedelta(seconds=1))
    assert (
        enroll(following, section, following_user, EnrollOptions(waitlist_if_full=True)).waitlist_entry.position() == 2
    )

    # The first in line registers for another section at the same time meanwhile.
    overlapping = make_section(setup["term"], meeting={"weekday": 1, "start_time": "09:30", "end_time": "10:30"})
    assert enroll(conflicted, overlapping, conflicted_user).succeeded()

    with django_capture_on_commit_callbacks(execute=True):
        DropEnrollment().drop(Enrollment.objects.get(student_record=holder), holder_user)

    assert WaitlistEntry.objects.get(student_record=conflicted).status == WaitlistStatus.REMOVED
    assert Enrollment.objects.get(student_record=following, section=section).status == EnrollmentStatus.ENROLLED
    section.refresh_from_db()
    assert section.enrolled_count == 1
    recipients = {address for message in mailoutbox for address in message.to}
    assert following_user.email in recipients
    assert conflicted_user.email in recipients


def test_lets_staff_waive_a_rule_with_a_reason_and_honours_overrides(
    setup: dict[str, Any], make_student: Any, make_section: Any
) -> None:
    record, user = make_student(setup["program"])
    restricted = make_section(setup["term"], eligibility=TargetCriteria(year_levels=(4,)))
    staff = setup["staff"]

    assert enroll(record, restricted, user).outcome == AttemptOutcome.REFUSED
    with pytest.raises(ValidationError):
        enroll(record, restricted, staff, EnrollOptions(waive=(RuleCode.ELIGIBILITY,)))
    assert enroll(
        record, restricted, staff, EnrollOptions(waive=(RuleCode.ELIGIBILITY,), reason="Approved by the department")
    ).succeeded()

    other, other_user = make_student(setup["program"])
    ManageHolds().grant_override(
        other, setup["term"], RuleCode.ELIGIBILITY, "Exchange student", staff, section_id=restricted.pk
    )
    assert enroll(other, restricted, other_user).succeeded()


def test_drops_only_while_registration_or_add_drop_is_open_unless_staff_do_it(
    setup: dict[str, Any], make_student: Any, make_section: Any
) -> None:
    record, user = make_student(setup["program"])
    section = make_section(setup["term"])
    enrollment = enroll(record, section, user).enrollment
    TermWindow.objects.filter(term=setup["term"]).update(closes_at=now() - timedelta(minutes=1))

    with pytest.raises(ValidationError):
        DropEnrollment().drop(enrollment, user)

    DropEnrollment().drop(enrollment, setup["staff"], "Medical reasons")
    enrollment.refresh_from_db()
    assert enrollment.status == EnrollmentStatus.DROPPED
    section.refresh_from_db()
    assert section.enrolled_count == 0
