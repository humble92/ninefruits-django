"""Registration pieces beyond the original test files: the hold CSV import, the rule catalog
seeder and profile idempotency, waitlist expiry and the per-section promotion lock, the cart
pre-check, retake parameters, and the evaluation method guard of ``UpdateSection`` (deferred
from Phase 4 until enrollments existed)."""

from __future__ import annotations

from datetime import timedelta
from typing import Any

import pytest
from django.core.cache import cache
from django.core.exceptions import ValidationError

from ninefruits.grading.enums import EvaluationMethod
from ninefruits.importing.services import start_import
from ninefruits.offering.actions import UpdateSection
from ninefruits.registration import tasks
from ninefruits.registration.actions import ManageCart, PrepareRuleSet, PromoteWaitlist
from ninefruits.registration.enums import GradeStatus, HoldType, RuleCode, WaitlistStatus
from ninefruits.registration.models import RegistrationHold, RegistrationRule, RegistrationRuleSet
from ninefruits.registration.services.rule_catalog import RuleCatalog
from ninefruits.security.enums import Permission
from ninefruits.setup.seeders.essential.registration_rules import RegistrationRuleCatalogSeeder
from ninefruits.term.enums import TermWindowType
from ninefruits.term.models import TermWindow
from tests.factories.offering import SectionFactory
from tests.factories.person import StudentRecordFactory
from tests.factories.registration import EnrollmentFactory, WaitlistEntryFactory
from tests.factories.security import UserFactory

from .conftest import enroll, now, open_registration, open_window, upcoming_term

pytestmark = pytest.mark.django_db


def test_imports_holds_from_csv_and_reports_unknown_students() -> None:
    record = StudentRecordFactory()
    staff = UserFactory(permissions=[Permission.REGISTRATION_HOLDS_MANAGE])
    rows = [
        {
            "student_number": record.student_number,
            "hold_type": "financial",
            "reason": "Unpaid",
            "ends_at": "2099-01-01",
        },
        {"student_number": "NOPE", "hold_type": "financial", "reason": "Unpaid"},
        {"student_number": record.student_number, "hold_type": "nonsense", "reason": "Bad type"},
        {
            "student_number": record.student_number,
            "hold_type": "academic",
            "reason": "Ends before it starts",
            "starts_at": "2030-01-02 09:00",
            "ends_at": "2030-01-01",
        },
    ]

    run = start_import("registration_holds", staff, "holds.csv", "imports/holds.csv", rows, queue=False)

    hold = RegistrationHold.objects.get(student_record=record)
    assert hold.hold_type == HoldType.FINANCIAL
    assert hold.source == "import"
    assert hold.blocks_registration is True
    assert hold.ends_at is not None
    assert run.successful_rows == 1
    reasons = [row.validation_error for row in run.failed_rows.order_by("id")]
    assert "No student record with number NOPE." in reasons[0]
    assert len(reasons) == 3


def test_adds_rules_new_to_the_catalog_to_existing_rule_sets_and_keeps_edits() -> None:
    term = upcoming_term()
    rule_set = PrepareRuleSet().handle(term, None, None)
    RegistrationRule.objects.filter(rule_set=rule_set, rule_code=RuleCode.HOLD).update(severity="warn")
    RegistrationRule.objects.filter(rule_set=rule_set, rule_code=RuleCode.REPEAT_COURSE).delete()

    RegistrationRuleCatalogSeeder()()
    RegistrationRuleCatalogSeeder()()

    assert rule_set.rules.count() == len(RuleCatalog().configurable()) == 8
    assert rule_set.rules.get(rule_code=RuleCode.HOLD).severity == "warn"
    assert rule_set.rules.get(rule_code=RuleCode.REPEAT_COURSE).parameters == {
        "allowed": True,
        "max_attempts": None,
        "below_grade": None,
    }


def test_refuses_a_second_rule_set_for_a_term() -> None:
    term = upcoming_term()
    PrepareRuleSet().handle(term, None, None)
    with pytest.raises(ValidationError):
        PrepareRuleSet().handle(term, None, None)
    assert RegistrationRuleSet.objects.filter(term=term).count() == 1


def test_expires_the_waitlist_when_registration_has_closed(mailoutbox: list[Any]) -> None:
    term = upcoming_term()
    section = SectionFactory(term=term, published=True, capacity=1, waitlist_capacity=3)
    entry = WaitlistEntryFactory(section=section, student_record=StudentRecordFactory())

    counts = PromoteWaitlist().handle(section)

    entry.refresh_from_db()
    assert counts == {"promoted": 0, "removed": 0, "expired": 1}
    assert entry.status == WaitlistStatus.EXPIRED
    assert entry.outcome_note == "Registration closed before a seat became free."


def test_runs_one_promotion_per_section_at_a_time(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[int] = []
    monkeypatch.setattr(PromoteWaitlist, "handle", lambda self, section: calls.append(section.pk) or {})
    section = SectionFactory(published=True)
    cache.add(tasks.promotion_lock_key(section.pk), "1", 60)
    try:
        assert tasks.promote_waitlist.apply(args=[section.pk]).get() is None
    finally:
        cache.delete(tasks.promotion_lock_key(section.pk))
    tasks.promote_waitlist.apply(args=[section.pk]).get()
    assert calls == [section.pk]


def test_keeps_a_student_waiting_who_only_lacks_a_reserved_seat(make_student: Any) -> None:
    from ninefruits.core.targeting import TargetCriteria
    from ninefruits.offering.models import SectionSeatGroup

    term = upcoming_term()
    open_registration(term)
    section = SectionFactory(term=term, published=True, capacity=1, waitlist_capacity=3)
    SectionSeatGroup.objects.create(
        section=section,
        name={"en": "Majors"},
        capacity=1,
        eligibility=TargetCriteria(year_levels=(4,)),
        releases_at=now() + timedelta(days=1),
    )
    record, _user = make_student(year_level=1)
    entry = WaitlistEntryFactory(section=section, student_record=record)

    PromoteWaitlist().handle(section)

    entry.refresh_from_db()
    assert entry.status == WaitlistStatus.WAITING


def test_the_cart_stops_only_on_the_window_section_state_and_duplicates(make_student: Any, make_section: Any) -> None:
    term = upcoming_term()
    open_window(term, TermWindowType.REGISTRATION_CART)
    record, user = make_student(year_level=1)
    from ninefruits.core.targeting import TargetCriteria

    restricted = make_section(term, eligibility=TargetCriteria(year_levels=(4,)))
    evaluation = ManageCart().add(record, restricted, user)
    assert RuleCode.ELIGIBILITY in {result.code for result in evaluation.blocking()}

    draft = SectionFactory(term=term)
    with pytest.raises(ValidationError):
        ManageCart().add(record, draft, user)

    TermWindow.objects.filter(term=term).delete()
    with pytest.raises(ValidationError):
        ManageCart().add(
            record, make_section(term, meeting={"weekday": 3, "start_time": "09:00", "end_time": "10:00"}), user
        )


@pytest.mark.parametrize(
    ("parameters", "message"),
    [
        ({"allowed": False}, "You have already taken this course and retakes are not allowed."),
        ({"max_attempts": 1}, "You have reached the maximum of 1 attempts for this course."),
        ({"below_grade": "C0"}, "Retakes are allowed only for grades below C0."),
        ({}, None),
    ],
)
def test_applies_the_retake_parameters(
    make_student: Any, make_section: Any, parameters: dict[str, Any], message: str | None
) -> None:
    from tests.factories.term import TermFactory

    term = upcoming_term()
    open_registration(term)
    record, user = make_student()
    section = make_section(term)
    earlier = SectionFactory(
        term=TermFactory(
            start_date=term.start_date - timedelta(days=400), end_date=term.start_date - timedelta(days=300)
        ),
        course=section.course,
        published=True,
    )
    EnrollmentFactory(section=earlier, student_record=record, grade="B0")
    rule_set = PrepareRuleSet().handle(term, None, None)
    rule = rule_set.rules.get(rule_code=RuleCode.REPEAT_COURSE)
    rule.parameters = {**rule.parameters, **parameters}
    rule.save()

    outcome = enroll(record, section, user)

    if message is None:
        assert outcome.succeeded()
        assert outcome.enrollment.is_retake
        assert "This registration is a retake." in outcome.messages() or not outcome.messages()
    else:
        assert outcome.messages() == [message]


def test_refuses_an_evaluation_method_change_once_grades_are_entered() -> None:
    manager = UserFactory(permissions=[Permission.SECTIONS_MANAGE])
    section = SectionFactory(published=True, evaluation_method=EvaluationMethod.RELATIVE)
    enrollment = EnrollmentFactory(section=section)

    UpdateSection()(section, {"evaluation_method": EvaluationMethod.ABSOLUTE}, manager)
    section.refresh_from_db()
    assert section.evaluation_method == EvaluationMethod.ABSOLUTE

    type(enrollment).objects.filter(pk=enrollment.pk).update(grade_status=GradeStatus.DRAFT)
    with pytest.raises(ValidationError):
        UpdateSection()(section, {"evaluation_method": EvaluationMethod.RELATIVE}, manager)


def test_refuses_a_capacity_below_the_registered_students(make_student: Any, make_section: Any) -> None:
    term = upcoming_term()
    open_registration(term)
    section = make_section(term, capacity=2)
    for _ in range(2):
        record, user = make_student()
        assert enroll(record, section, user).succeeded()
    manager = UserFactory(permissions=[Permission.SECTIONS_MANAGE])
    section.refresh_from_db()
    with pytest.raises(ValidationError):
        UpdateSection()(section, {"capacity": 1}, manager)
