"""Registration admin screens on the tiny demo (original ``tests/Feature/Admin/RegistrationAdminTest.php``
and the Phase 5 datasets of ``AdminPagesTest.php``): consistent demo registrations, every page,
staff registration from the section roster with waived rules and drop with a reason, holds and
overrides, preparing a rule set and editing a rule's parameters, credit limits, capacity kept at
or above the registrations, the waitlist tab."""

from __future__ import annotations

from collections.abc import Iterator
from datetime import timedelta
from typing import Any

import pytest
from django.db.models import F
from django.test import Client
from django.utils import timezone

from ninefruits.core.db import session_context
from ninefruits.offering.models import Section
from ninefruits.person.enums import StudentStatus
from ninefruits.person.models import StudentRecord
from ninefruits.registration.enums import EnrollmentSource, EnrollmentStatus, HoldType, RuleCode, RuleSeverity
from ninefruits.registration.models import (
    CreditLimitPolicy,
    Enrollment,
    RegistrationHold,
    RegistrationOverride,
    RegistrationRuleSet,
    WaitlistEntry,
)
from ninefruits.security.enums import Permission
from ninefruits.security.models import User
from ninefruits.setup.seeders.demo import DemoOptions, use_options
from ninefruits.setup.seeders.demo.accounts import DemoAccountSeeder
from ninefruits.setup.seeders.demo.curriculum import DemoCurriculumSeeder
from ninefruits.setup.seeders.demo.people import DemoPeopleSeeder
from ninefruits.setup.seeders.demo.reference import DemoReferenceSeeder
from ninefruits.setup.seeders.demo.registration import DemoRegistrationSeeder
from tests.factories.security import UserFactory
from tests.factories.term import TermFactory

pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def demo(essential_data: None) -> Iterator[None]:
    # The smallest demo that still has every kind of data, seeded like setup_demo does.
    with use_options(DemoOptions(size="tiny", seed=42)):
        for seeder in (
            DemoAccountSeeder,
            DemoReferenceSeeder,
            DemoPeopleSeeder,
            DemoCurriculumSeeder,
            DemoRegistrationSeeder,
        ):
            seeder()()
    yield


@pytest.fixture
def manager() -> User:
    return UserFactory(permissions=list(Permission))


@pytest.fixture
def enrollment() -> Enrollment:
    """A registration in a section with free seats (the demo also has a full next-term section
    with a waitlist)."""
    return (
        Enrollment.objects.filter(status=EnrollmentStatus.ENROLLED, section__enrolled_count__lt=F("section__capacity"))
        .select_related("section__course", "student_record")
        .order_by("id")
        .first()
    )


def signed_in(user: User) -> Client:
    client = Client()
    client.force_login(user)
    session_context().reset()
    return client


def test_seeds_consistent_demo_registrations() -> None:
    assert Enrollment.objects.exists()
    assert WaitlistEntry.objects.exists()
    assert RegistrationHold.objects.count() == 2
    assert RegistrationRuleSet.objects.count() == 2
    for section in Section.objects.all():
        held = section.enrollments.filter(status__in=[EnrollmentStatus.ENROLLED, EnrollmentStatus.COMPLETED]).count()
        assert section.enrolled_count == held
        assert section.enrolled_count <= section.capacity


def test_renders_the_registration_pages(manager: User, enrollment: Enrollment) -> None:
    client = signed_in(manager)
    rule_set = RegistrationRuleSet.objects.order_by("id").first()
    rule = rule_set.rules.order_by("id").first()
    hold = RegistrationHold.objects.order_by("id").first()
    override_page = "/admin/registration/registrationoverride/"
    pages = [
        "/admin/registration/enrollment/",
        "/admin/registration/enrollment/register-student/",
        f"/admin/registration/enrollment/{enrollment.pk}/drop/",
        f"/admin/registration/enrollment/{enrollment.pk}/withdraw/",
        "/admin/registration/registrationhold/",
        "/admin/registration/registrationhold/place/",
        f"/admin/registration/registrationhold/{hold.pk}/release/",
        "/admin/registration/registrationhold/import-csv/",
        override_page,
        f"{override_page}grant/",
        "/admin/registration/registrationruleset/",
        "/admin/registration/registrationruleset/prepare/",
        f"/admin/registration/registrationruleset/{rule_set.pk}/change/",
        f"/admin/registration/registrationrule/{rule.pk}/change/",
        "/admin/registration/creditlimitpolicy/",
        "/admin/registration/creditlimitpolicy/add/",
        f"/admin/registration/creditlimitpolicy/{CreditLimitPolicy.objects.order_by('id').first().pk}/change/",
        "/admin/registration/registrationattempt/",
        f"/admin/offering/section/{enrollment.section_id}/change/",
        f"/admin/offering/section/{enrollment.section_id}/register-student/",
    ]
    for url in pages:
        assert client.get(url).status_code == 200, url

    roster = client.get(f"/admin/offering/section/{enrollment.section_id}/change/").content.decode()
    assert enrollment.student_record.student_number in roster
    assert "data-roster" in roster

    student = User.objects.get(email="student@demo.test")
    page = signed_in(student).get("/portal/registration/")
    assert page.status_code == 200
    assert "Cart" in page.content.decode()


def test_renders_the_registration_pages_in_korean(manager: User) -> None:
    manager.locale = "ko"
    manager.save(update_fields=["locale"])
    page = signed_in(manager).get("/admin/registration/enrollment/").content.decode()
    assert "수강신청" in page


def test_registers_a_student_as_staff_with_a_waived_rule_and_drops_with_a_reason(
    manager: User, enrollment: Enrollment
) -> None:
    section = enrollment.section
    record = next(
        record
        for record in StudentRecord.objects.filter(status=StudentStatus.ENROLLED, holds__isnull=True).exclude(
            enrollments__term_id=section.term_id, enrollments__course_id=section.course_id
        )
        if section.admits(record)
    )
    client = signed_in(manager)

    response = client.post(
        f"/admin/offering/section/{section.pk}/register-student/",
        {
            "student_number": record.student_number,
            "waive": [RuleCode.REQUISITES.value, RuleCode.TIME_CONFLICT.value, RuleCode.CREDIT_LIMIT.value],
            "reason": "Advisor approval",
        },
    )
    assert response.status_code == 302

    registered = Enrollment.objects.get(student_record=record, section=section)
    assert registered.source == EnrollmentSource.STAFF

    response = client.post(
        f"/admin/registration/enrollment/{registered.pk}/drop/", {"reason": "Requested by the student"}
    )
    assert response.status_code == 302
    registered.refresh_from_db()
    assert registered.status == EnrollmentStatus.DROPPED


def test_places_and_releases_a_hold_and_grants_an_override(manager: User, enrollment: Enrollment) -> None:
    record = enrollment.student_record
    client = signed_in(manager)

    client.post(
        "/admin/registration/registrationhold/place/",
        {
            "student_number": record.student_number,
            "hold_type": HoldType.ACADEMIC.value,
            "blocks_registration": "on",
            "reason": "Probation meeting",
        },
    )
    hold = RegistrationHold.objects.get(student_record=record, hold_type=HoldType.ACADEMIC)

    client.post(f"/admin/registration/registrationhold/{hold.pk}/release/", {"reason": "Met the advisor"})
    hold.refresh_from_db()
    assert hold.released_at is not None

    client.post(
        "/admin/registration/registrationoverride/grant/",
        {
            "student_number": record.student_number,
            "term_id": enrollment.term_id,
            "rule_code": RuleCode.CREDIT_LIMIT.value,
            "reason": "Graduating senior",
        },
    )
    assert RegistrationOverride.objects.get(student_record=record).rule_code == RuleCode.CREDIT_LIMIT

    override = RegistrationOverride.objects.get(student_record=record)
    client.post(f"/admin/registration/registrationoverride/{override.pk}/revoke/", {})
    override.refresh_from_db()
    assert override.revoked_at is not None


def test_prepares_a_rule_set_by_copying_and_edits_a_rule_with_its_parameters(manager: User) -> None:
    today = timezone.localdate()
    term = TermFactory(published=True, start_date=today + timedelta(days=365), end_date=today + timedelta(days=480))
    source = RegistrationRuleSet.objects.order_by("id").first()
    client = signed_in(manager)

    client.post("/admin/registration/registrationruleset/prepare/", {"term_id": term.pk, "copy_from_id": source.pk})

    rule_set = RegistrationRuleSet.objects.get(term=term)
    assert rule_set.copied_from_rule_set_id == source.pk
    rule = rule_set.rules.get(rule_code=RuleCode.TIME_CONFLICT)

    response = client.post(
        f"/admin/registration/registrationrule/{rule.pk}/change/",
        {
            "is_enabled": "on",
            "allows_override": "on",
            "severity": RuleSeverity.WARN.value,
            "allowed_overlap_minutes": "15",
        },
    )
    assert response.status_code == 302
    rule.refresh_from_db()
    assert rule.severity == RuleSeverity.WARN
    assert rule.parameters == {"allowed_overlap_minutes": 15}
    assert rule_set.rules.get(rule_code=RuleCode.HOLD).parameters is None


def test_creates_a_credit_limit_for_a_group_of_students(manager: User) -> None:
    response = signed_in(manager).post(
        "/admin/registration/creditlimitpolicy/add/",
        {
            "name__en": "Honors",
            "priority": "50",
            "max_credits": "24",
            "is_active": "on",
            "eligibility__year_levels": ["4"],
        },
    )
    assert response.status_code == 302, response.content.decode()[:2000]
    assert list(CreditLimitPolicy.objects.get(priority=50).eligibility.year_levels) == [4]


def test_keeps_capacity_at_or_above_the_registered_students(manager: User) -> None:
    section = Section.objects.filter(enrolled_count__gt=1).select_related("term").order_by("id").first()
    client = signed_in(manager)
    data: dict[str, Any] = {
        "term_session_id": str(section.session_id),
        "section_code": section.section_code,
        "capacity": "0",
        "evaluation_method": section.evaluation_method,
        "waitlist_capacity": str(section.waitlist_capacity),
        "org_unit": str(section.org_unit_id),
    }
    for prefix in ("meetings", "instructor_assignments", "seat_groups"):
        data[f"{prefix}-TOTAL_FORMS"] = "0"
        data[f"{prefix}-INITIAL_FORMS"] = "0"

    client.post(f"/admin/offering/section/{section.pk}/change/", data)

    section.refresh_from_db()
    assert section.capacity > 0


def test_lists_the_waitlist_and_removes_an_entry_with_a_reason(manager: User) -> None:
    entry = WaitlistEntry.objects.select_related("section", "student_record").order_by("id").first()
    client = signed_in(manager)

    page = client.get(f"/admin/offering/section/{entry.section_id}/change/").content.decode()
    assert "data-waitlist" in page
    assert entry.student_record.student_number in page

    client.post(f"/admin/offering/section/{entry.section_id}/waitlist/{entry.pk}/remove/", {"reason": "Changed plans"})
    entry.refresh_from_db()
    assert entry.status == "removed"


def test_promotes_the_waitlist_now_after_a_capacity_increase(manager: User) -> None:
    entry = WaitlistEntry.objects.filter(status="waiting").select_related("section").order_by("id").first()
    Section.objects.filter(pk=entry.section_id).update(capacity=F("capacity") + 1)
    client = signed_in(manager)

    client.post(f"/admin/offering/section/{entry.section_id}/promote-waitlist/", {})

    entry.refresh_from_db()
    section = Section.objects.get(pk=entry.section_id)
    # Every rule is checked again: registration for the next term is open only for fourth-year
    # students in the demo, so the first in line is promoted or taken off with the reason.
    assert entry.status in {"promoted", "removed"}
    if entry.status == "removed":
        assert entry.outcome_note
    assert section.enrolled_count <= section.capacity
