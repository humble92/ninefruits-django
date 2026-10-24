"""Fixtures for the graduation tests (original ``beforeEach`` of
``tests/Feature/Graduation/GraduationTest.php``): essential data and the 4.5 grade scale, a
graduation staff member, a fourth-year student of catalog year 2024 with an account, a term in
2025, course categories (general with a required subcategory, major), six courses and the
program's primary requirement set from 2020 (12 credits): 6 credits in general, MAJ201 required,
two of MAJ202/MAJ203. The minimum cumulative GPA is switched off unless a test sets it."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Any

import pytest
from django.test import Client

from ninefruits.core.db import session_context
from ninefruits.curriculum.enums import ProgramRole, RequirementKind
from ninefruits.curriculum.models import CurriculumRequirement, CurriculumRequirementCourse, CurriculumRequirementSet
from ninefruits.graduation.settings import GraduationSettings
from ninefruits.security.enums import MfaEnforcement, Permission
from ninefruits.settings.groups.security import SecuritySettings
from tests.factories.curriculum import CourseCategoryFactory, CourseFactory
from tests.factories.offering import SectionFactory
from tests.factories.person import StudentRecordFactory
from tests.factories.registration import EnrollmentFactory
from tests.factories.security import UserFactory
from tests.factories.term import TermFactory
from tests.reference_conftest import *  # noqa: F403

STAFF_PERMISSIONS = [
    Permission.ADMIN_PANEL_ACCESS,
    Permission.GRADUATION_AUDIT,
    Permission.GRADUATION_PROCESS,
    Permission.REPORTS_VIEW,
    Permission.STUDENT_RECORDS_VIEW,
    Permission.STUDENT_STATUS_CHANGES_APPROVE,
]


def signed_in(user: Any) -> Client:
    client = Client()
    client.force_login(user)
    session_context().reset()
    return client


def set_minimum_gpa(value: float | None) -> None:
    settings = GraduationSettings.load()
    settings.minimum_cumulative_gpa = value
    settings.save()


def pass_course(record: Any, term: Any, course: Any, grade: str = "A0") -> Any:
    """Original ``pass()``: a completed enrollment in a published section of the course."""
    section = SectionFactory(published=True, term=term, course=course)
    return EnrollmentFactory(section=section, student_record=record, grade=grade)


@pytest.fixture(autouse=True)
def _mfa_not_used(request: pytest.FixtureRequest) -> None:
    if "db" not in request.fixturenames and request.node.get_closest_marker("django_db") is None:
        return
    request.getfixturevalue("db")
    settings = SecuritySettings.load()
    settings.mfa_enforcement = MfaEnforcement.DISABLED
    settings.save()


@pytest.fixture
def profile(essential_data: None) -> None:
    """The Korean university profile (its examination kinds)."""
    from ninefruits.setup.seeders.profiles.korean_university import KoreanUniversityProfileSeeder

    KoreanUniversityProfileSeeder()()


@pytest.fixture
def world(essential_data: None, as_user: Any) -> dict[str, Any]:
    from tests.factories.registration import default_scale_item

    default_scale_item("A0")  # the 4.5 scale (original GradeScale::factory()->korean())
    staff = UserFactory(permissions=STAFF_PERMISSIONS)
    record = StudentRecordFactory(catalog_year=2024, year_level=4)
    student = UserFactory(person=record.person)
    term = TermFactory(published=True, start_date=date(2025, 3, 1), end_date=date(2025, 6, 20))

    general = CourseCategoryFactory(code="GEN")
    general_required = CourseCategoryFactory(code="GEN_REQ", parent=general)
    major = CourseCategoryFactory(code="MAJ")
    categories = {
        "GEN101": general_required,
        "GEN102": general,
        "MAJ201": major,
        "MAJ202": major,
        "MAJ203": major,
        "OLD201": major,
    }
    courses = {
        code: CourseFactory(code=code, version={"category": category, "credits": Decimal("3")})
        for code, category in categories.items()
    }
    requirement_set = CurriculumRequirementSet.objects.create(
        program_id=record.program_id,
        program_role=ProgramRole.PRIMARY,
        catalog_year_from=2020,
        total_credits=Decimal("12"),
        name={"en": "Requirements 2020", "ko": "2020 요건", "zh-hans": "2020 要求"},
    )

    def line(kind: RequirementKind, course_codes: list[str] = (), **attributes: Any) -> CurriculumRequirement:  # type: ignore[assignment]
        requirement = CurriculumRequirement.objects.create(requirement_set=requirement_set, kind=kind, **attributes)
        for code in course_codes:
            CurriculumRequirementCourse.objects.create(requirement=requirement, course=courses[code])
        return requirement

    general_line = line(RequirementKind.CATEGORY_CREDITS, category=general, min_credits=Decimal("6"), sort_order=1)
    required_line = line(RequirementKind.REQUIRED_COURSES, ["MAJ201"], sort_order=2)
    group_line = line(RequirementKind.COURSE_GROUP, ["MAJ202", "MAJ203"], min_courses=2, sort_order=3)

    # Most cases have no term record (no GPA): the default 2.0 minimum is off unless a test sets it.
    set_minimum_gpa(None)
    return {
        "staff": staff,
        "record": record,
        "student": student,
        "term": term,
        "general": general,
        "major": major,
        "courses": courses,
        "set": requirement_set,
        "general_line": general_line,
        "required_line": required_line,
        "group_line": group_line,
        "as_user": as_user,
    }


def act(world: dict[str, Any], user: Any, call: Any) -> Any:
    """Runs an action with the user's database context (row level security applies)."""
    with world["as_user"](user):
        return call()
