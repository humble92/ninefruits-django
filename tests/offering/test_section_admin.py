"""Section screens without demo data: scope of the list, seat group capacity, copying from the
list, instructor assignment on the instructors tab."""

from __future__ import annotations

from datetime import date

import pytest
from django.contrib.messages import get_messages
from django.test import Client

from ninefruits.offering.models import Section
from ninefruits.security.enums import MfaEnforcement, Permission, ScopeType
from ninefruits.security.models import User
from ninefruits.settings.groups.security import SecuritySettings
from tests.factories.curriculum import CourseFactory
from tests.factories.offering import SectionFactory
from tests.factories.organization import OrgUnitFactory
from tests.factories.person import InstructorFactory
from tests.factories.security import UserFactory
from tests.factories.term import TermFactory

pytestmark = [pytest.mark.django_db, pytest.mark.usefixtures("essential_data")]


@pytest.fixture(autouse=True)
def _mfa_not_used(essential_data: None) -> None:
    settings = SecuritySettings.load()
    settings.mfa_enforcement = MfaEnforcement.DISABLED
    settings.save()


def signed_in(user: User) -> Client:
    client = Client()
    client.force_login(user)
    return client


def change_data(section: Section, prefix_rows: dict[str, list[dict[str, str]]] | None = None) -> dict[str, object]:
    data: dict[str, object] = {
        "term_session_id": str(section.session_id),
        "section_code": section.section_code,
        "capacity": str(section.capacity),
        "evaluation_method": section.evaluation_method,
        "waitlist_capacity": "0",
        "org_unit": str(section.org_unit_id),
    }
    for prefix in ("meetings", "instructor_assignments", "seat_groups"):
        rows = (prefix_rows or {}).get(prefix, [])
        data[f"{prefix}-TOTAL_FORMS"] = str(len(rows))
        data[f"{prefix}-INITIAL_FORMS"] = "0"
        for index, row in enumerate(rows):
            data.update({f"{prefix}-{index}-{key}": value for key, value in row.items()})
    return data


def test_department_staff_see_and_change_only_their_units_sections() -> None:
    unit, other_unit = OrgUnitFactory(), OrgUnitFactory()
    term = TermFactory(published=True)
    own = SectionFactory(term=term, course=CourseFactory(org_unit=unit))
    other = SectionFactory(term=term, course=CourseFactory(org_unit=other_unit))
    staff = UserFactory(
        permissions=[Permission.ADMIN_PANEL_ACCESS, Permission.SECTIONS_MANAGE],
        permissions__scope_type=ScopeType.ORG_UNIT,
        permissions__scope_id=unit.pk,
    )
    client = signed_in(staff)

    page = client.get("/admin/offering/section/", {"term": "all"}).content.decode()
    assert own.label() in page
    assert other.label() not in page
    assert client.get(f"/admin/offering/section/{own.pk}/change/").status_code == 200
    assert client.get(f"/admin/offering/section/{other.pk}/change/").status_code == 302  # not found: back to list


def test_refuses_reserved_seats_beyond_the_capacity() -> None:
    manager = UserFactory(permissions=list(Permission))
    section = SectionFactory(capacity=40)
    response = signed_in(manager).post(
        f"/admin/offering/section/{section.pk}/change/",
        change_data(
            section,
            {"seat_groups": [{"name__en": "Majors", "capacity": "50", "sort_order": "0"}]},
        ),
    )
    assert response.status_code == 200
    assert "Reserved seats together exceed the section capacity (40)." in response.content.decode()
    assert section.seat_groups.count() == 0


def test_assigns_an_instructor_on_the_instructors_tab() -> None:
    manager = UserFactory(permissions=list(Permission))
    section = SectionFactory()
    instructor = InstructorFactory()
    response = signed_in(manager).post(
        f"/admin/offering/section/{section.pk}/change/",
        change_data(section, {"instructor_assignments": [{"instructor": str(instructor.pk), "role": "primary"}]}),
    )
    assert response.status_code == 302, response.content.decode()[:3000]
    assert list(section.instructors.values_list("pk", flat=True)) == [instructor.pk]


def test_copies_sections_from_the_list_with_a_preview() -> None:
    manager = UserFactory(permissions=list(Permission))
    fall = TermFactory(published=True, start_date=date(2026, 9, 1), end_date=date(2026, 12, 20))
    spring = TermFactory(published=True, start_date=date(2027, 3, 2), end_date=date(2027, 6, 20))
    SectionFactory(term=fall)
    client = signed_in(manager)

    response = client.post(
        "/admin/offering/section/copy-sections/",
        {"from_term_id": str(fall.pk), "to_term_id": str(spring.pk), "dry_run": "on"},
    )
    assert response.status_code == 302
    assert any("Preview: 1 section(s)" in str(m) for m in get_messages(response.wsgi_request))
    assert not Section.objects.filter(term=spring).exists()

    response = client.post(
        "/admin/offering/section/copy-sections/", {"from_term_id": str(fall.pk), "to_term_id": str(spring.pk)}
    )
    assert response.status_code == 302
    assert Section.objects.filter(term=spring).count() == 1


def test_sidebar_lists_the_curriculum_screens_and_hides_course_versions() -> None:
    from django.contrib import admin
    from django.test import RequestFactory

    from ninefruits.adminpanel.navigation import build_navigation

    request = RequestFactory().get("/admin/")
    request.user = UserFactory(permissions=list(Permission))
    groups = {
        group["title"]: [item["link"] for item in group["items"]] for group in build_navigation(admin.site, request)
    }
    links = groups["Curriculum and sections"]
    assert links == [
        "/admin/curriculum/course/",
        "/admin/curriculum/curriculumrequirementset/",
        "/admin/offering/section/",
        "/admin/offering/timetables/",
    ]


def test_instructors_without_staff_permissions_cannot_open_the_section_screens() -> None:
    user = UserFactory(permissions=[Permission.ADMIN_PANEL_ACCESS])
    section = SectionFactory()
    client = signed_in(user)
    assert client.get("/admin/offering/section/").status_code == 403
    assert client.get(f"/admin/offering/section/{section.pk}/change/").status_code == 403
    assert client.get("/admin/offering/timetables/").status_code == 403


def test_renders_the_section_screens_in_korean() -> None:
    manager = UserFactory(permissions=list(Permission), locale="ko")
    section = SectionFactory()
    client = signed_in(manager)
    page = client.get(f"/admin/offering/section/{section.pk}/change/").content.decode()
    assert "강의 시간" in page
    assert "개설강좌" in client.get("/admin/offering/section/").content.decode()


def test_saves_eligibility_exclusion_and_note_from_the_section_form() -> None:
    manager = UserFactory(permissions=list(Permission))
    section = SectionFactory()
    response = signed_in(manager).post(
        f"/admin/offering/section/{section.pk}/change/",
        {
            **change_data(section),
            "capacity": "35",
            "note__en": "Bring a laptop",
            "eligibility__year_levels": ["1", "2"],
            "exclusion__org_unit_ids": [str(section.org_unit_id)],
        },
    )
    assert response.status_code == 302, response.content.decode()[:3000]
    section.refresh_from_db()
    assert section.capacity == 35
    assert section.note_translations == {"en": "Bring a laptop"}
    assert section.eligibility.year_levels == [1, 2]
    assert section.exclusion.org_unit_ids == [section.org_unit_id]
