"""Course and graduation requirement screens (original CourseResource, VersionsRelationManager
revise action and CurriculumRequirementSetResource behaviour)."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest
from django.contrib.messages import get_messages
from django.test import Client

from ninefruits.curriculum.enums import ProgramRole, RequirementKind
from ninefruits.curriculum.models import Course, CourseVersion, CurriculumRequirementSet
from ninefruits.security.enums import MfaEnforcement, Permission
from ninefruits.security.models import User
from ninefruits.settings.groups.security import SecuritySettings
from tests.factories.curriculum import CourseCategoryFactory, CourseFactory, CurriculumRequirementSetFactory
from tests.factories.organization import OrgUnitFactory, ProgramFactory
from tests.factories.security import UserFactory

pytestmark = [pytest.mark.django_db, pytest.mark.usefixtures("essential_data")]


@pytest.fixture(autouse=True)
def _mfa_not_used(essential_data: None) -> None:
    settings = SecuritySettings.load()
    settings.mfa_enforcement = MfaEnforcement.DISABLED
    settings.save()


@pytest.fixture
def manager() -> User:
    return UserFactory(
        permissions=[Permission.ADMIN_PANEL_ACCESS, Permission.COURSES_MANAGE, Permission.CURRICULUM_MANAGE]
    )


def signed_in(user: User) -> Client:
    client = Client()
    client.force_login(user)
    return client


def test_creates_a_course_with_its_first_version(manager: User) -> None:
    unit = OrgUnitFactory(code="CSE")
    category = CourseCategoryFactory()
    response = signed_in(manager).post(
        "/admin/curriculum/course/add/",
        {
            "code": "CSE2010",
            "org_unit": str(unit.pk),
            "is_active": "on",
            "effective_start_date": "2020-03-01",
            "title__en": "Data Structures",
            "title__ko": "자료구조",
            "credits": "3",
            "lecture_hours": "3",
            "lab_hours": "0",
            "category": str(category.pk),
            "grading_basis": "graded",
            "counts_toward_credit_limit": "on",
            "requires_evaluation": "on",
        },
    )
    assert response.status_code == 302, response.content.decode()[:3000]
    course = Course.objects.get(code="CSE2010")
    version = course.versions.get()
    assert version.title_translations == {"en": "Data Structures", "ko": "자료구조"}
    assert version.category_id == category.pk
    assert response["Location"].endswith(f"/admin/curriculum/course/{course.pk}/change/")


def test_revises_a_version_from_the_course_page(manager: User) -> None:
    course = CourseFactory(version={"effective_start_date": date(2020, 3, 1), "credits": 3})
    current = course.versions.get()
    client = signed_in(manager)
    assert "Revise from a date" in client.get(f"/admin/curriculum/course/{course.pk}/change/").content.decode()

    response = client.post(
        f"/admin/curriculum/course/{course.pk}/versions/{current.pk}/revise/",
        {
            "effective_from": "2027-03-01",
            "title__en": "Data Structures II",
            "credits": "4",
            "lecture_hours": "3",
            "lab_hours": "1",
            "grading_basis": "graded",
            "counts_toward_credit_limit": "on",
            "requires_evaluation": "on",
            "reason": "Lab added",
        },
    )
    assert response.status_code == 302, response.content.decode()[:3000]
    assert course.versions.count() == 2
    new = course.version_on(date(2027, 5, 1))
    assert new.credits == Decimal("4.0")
    assert str(new.title) == "Data Structures II"


def test_explains_an_overlapping_version_before_saving(manager: User) -> None:
    course = CourseFactory(version={"effective_start_date": date(2020, 3, 1)})
    response = signed_in(manager).post(
        "/admin/curriculum/courseversion/add/",
        {
            "course": str(course.pk),
            "effective_start_date": "2024-03-01",
            "title__en": "Overlap",
            "credits": "3",
            "lecture_hours": "3",
            "lab_hours": "0",
            "grading_basis": "graded",
            "requisites-TOTAL_FORMS": "0",
            "requisites-INITIAL_FORMS": "0",
        },
    )
    assert response.status_code == 200
    assert "This period overlaps another version of the course." in response.content.decode()
    assert CourseVersion.objects.filter(course=course).count() == 1


def test_saves_a_requirement_set_with_lines_and_explains_overlapping_catalog_years(manager: User) -> None:
    program = ProgramFactory()
    category = CourseCategoryFactory()
    course = CourseFactory()
    client = signed_in(manager)
    data = {
        "program": str(program.pk),
        "program_role": ProgramRole.PRIMARY,
        "catalog_year_from": "2015",
        "catalog_year_to": "2022",
        "name__en": "Requirements from 2015",
        "requirements-TOTAL_FORMS": "2",
        "requirements-INITIAL_FORMS": "0",
        "requirements-0-kind": RequirementKind.CATEGORY_CREDITS,
        "requirements-0-category": str(category.pk),
        "requirements-0-min_credits": "9",
        "requirements-0-sort_order": "1",
        "requirements-1-kind": RequirementKind.REQUIRED_COURSES,
        "requirements-1-course_ids": [str(course.pk)],
        "requirements-1-sort_order": "2",
    }
    response = client.post("/admin/curriculum/curriculumrequirementset/add/", data)
    assert response.status_code == 302, response.content.decode()[:3000]
    requirement_set = CurriculumRequirementSet.objects.get(program=program)
    lines = list(requirement_set.requirements.order_by("sort_order"))
    assert [line.kind for line in lines] == [RequirementKind.CATEGORY_CREDITS, RequirementKind.REQUIRED_COURSES]
    assert list(lines[1].courses.values_list("pk", flat=True)) == [course.pk]

    response = client.post(
        "/admin/curriculum/curriculumrequirementset/add/",
        {**data, "catalog_year_from": "2020", "catalog_year_to": "", "requirements-TOTAL_FORMS": "0"},
    )
    assert response.status_code == 200
    assert "These catalog years overlap another requirement set of the program and role." in response.content.decode()


def test_requires_the_category_for_category_credits(manager: User) -> None:
    requirement_set = CurriculumRequirementSetFactory()
    response = signed_in(manager).post(
        f"/admin/curriculum/curriculumrequirementset/{requirement_set.pk}/change/",
        {
            "program": str(requirement_set.program_id),
            "program_role": requirement_set.program_role,
            "catalog_year_from": str(requirement_set.catalog_year_from),
            "name__en": "Requirements",
            "requirements-TOTAL_FORMS": "1",
            "requirements-INITIAL_FORMS": "0",
            "requirements-0-kind": RequirementKind.CATEGORY_CREDITS,
            "requirements-0-sort_order": "1",
        },
    )
    assert response.status_code == 200
    assert requirement_set.requirements.count() == 0


def test_imports_courses_from_the_list_screen(manager: User) -> None:
    from django.core.files.uploadedfile import SimpleUploadedFile

    OrgUnitFactory(code="CSE")
    client = signed_in(manager)
    assert client.get("/admin/curriculum/course/import-csv/").status_code == 200
    upload = SimpleUploadedFile(
        "courses.csv", b"code,org_unit,effective_start_date,title_en,credits\nCSE1001,CSE,2020-03-01,Programming,3\n"
    )
    response = client.post("/admin/curriculum/course/import-csv/", {"file": upload})
    assert response.status_code == 302
    assert Course.objects.filter(code="CSE1001").exists()
    assert any("import finished" in str(message) for message in get_messages(response.wsgi_request))


def test_reference_viewers_see_courses_but_cannot_change_them() -> None:
    viewer = UserFactory(permissions=[Permission.ADMIN_PANEL_ACCESS, Permission.REFERENCE_DATA_VIEW])
    course = CourseFactory()
    client = signed_in(viewer)
    assert client.get("/admin/curriculum/course/").status_code == 200
    assert client.get("/admin/curriculum/course/add/").status_code == 403
    response = client.post(f"/admin/curriculum/course/{course.pk}/change/", {"code": "X"})
    assert response.status_code == 403
