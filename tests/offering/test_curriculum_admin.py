"""Original tests/Feature/Admin/CurriculumAdminTest.php (curriculum and section screens, room
timetable, portal catalog and teaching) and the Phase 4 datasets of AdminPagesTest.php. The
second major and minor cases of the original file are in the person tests (Phase 2)."""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any

import pytest
from django.contrib.messages import get_messages
from django.test import Client

from ninefruits.curriculum.models import Course, CourseVersion, CurriculumRequirementSet
from ninefruits.offering.enums import SectionStatus
from ninefruits.offering.models import Section
from ninefruits.security.enums import MfaEnforcement, Permission
from ninefruits.security.models import User
from ninefruits.settings.groups.security import SecuritySettings
from ninefruits.setup.seeders.demo import DemoOptions, use_options
from ninefruits.setup.seeders.demo.accounts import DemoAccountSeeder
from ninefruits.setup.seeders.demo.curriculum import DemoCurriculumSeeder
from ninefruits.setup.seeders.demo.people import DemoPeopleSeeder
from ninefruits.setup.seeders.demo.reference import DemoReferenceSeeder
from tests.factories.offering import SectionFactory
from tests.factories.security import UserFactory

pytestmark = [pytest.mark.django_db]


@pytest.fixture(autouse=True)
def demo(essential_data: None) -> Iterator[None]:
    settings = SecuritySettings.load()
    settings.mfa_enforcement = MfaEnforcement.DISABLED
    settings.save()
    with use_options(DemoOptions(size="tiny", seed=42)):
        for seeder in (DemoAccountSeeder, DemoReferenceSeeder, DemoPeopleSeeder, DemoCurriculumSeeder):
            seeder()()
    yield


@pytest.fixture
def manager() -> User:
    return UserFactory(permissions=list(Permission))


@pytest.fixture
def section() -> Section:
    return (
        Section.objects.filter(status=SectionStatus.PUBLISHED, meetings__room__isnull=False)
        .select_related("course", "term")
        .order_by("id")
        .first()
    )


def signed_in(user: User) -> Client:
    client = Client()
    client.force_login(user)
    return client


def test_renders_the_curriculum_and_section_pages(manager: User, section: Section) -> None:
    client = signed_in(manager)
    course = Course.objects.order_by("id").first()
    pages = [
        "/admin/curriculum/course/",
        "/admin/curriculum/course/add/",
        f"/admin/curriculum/course/{course.pk}/change/",
        f"/admin/curriculum/courseversion/{CourseVersion.objects.order_by('id').first().pk}/change/",
        f"/admin/curriculum/courseversion/add/?course={course.pk}",
        f"/admin/curriculum/course/{course.pk}/versions/{course.versions.first().pk}/revise/",
        "/admin/curriculum/curriculumrequirementset/",
        "/admin/curriculum/curriculumrequirementset/add/",
        f"/admin/curriculum/curriculumrequirementset/{CurriculumRequirementSet.objects.order_by('id').first().pk}/change/",
        "/admin/offering/section/",
        "/admin/offering/section/add/",
        f"/admin/offering/section/{section.pk}/change/",
        "/admin/offering/section/copy-sections/",
        "/admin/offering/timetables/",
        f"/admin/term/term/{section.term_id}/change/",
    ]
    for url in pages:
        assert client.get(url).status_code == 200, url


def _change_data(section: Section, meetings: list[dict[str, str]] | None = None) -> dict[str, Any]:
    data: dict[str, Any] = {
        "term_session_id": str(section.session_id),
        "section_code": section.section_code,
        "capacity": str(section.capacity),
        "evaluation_method": section.evaluation_method,
        "waitlist_capacity": str(section.waitlist_capacity),
        "org_unit": str(section.org_unit_id),
        "instruction_language": section.instruction_language or "",
        "note__en": "",
    }
    for prefix in ("meetings", "instructor_assignments", "seat_groups"):
        rows = meetings if prefix == "meetings" else []
        data[f"{prefix}-TOTAL_FORMS"] = str(len(rows or []))
        data[f"{prefix}-INITIAL_FORMS"] = "0"
        for index, row in enumerate(rows or []):
            data.update({f"{prefix}-{index}-{key}": value for key, value in row.items()})
    return data


def test_creates_a_section_and_explains_a_room_conflict_on_the_meetings_tab(manager: User, section: Section) -> None:
    taken = section.meetings.filter(room__isnull=False).first()
    course = (
        Course.objects.filter(is_active=True).exclude(versions__effective_end_date__isnull=False).order_by("id").first()
    )
    client = signed_in(manager)

    response = client.post(
        "/admin/offering/section/add/",
        {
            "term_session_id": str(section.term.full_term_session().pk),
            "course_id": str(course.pk),
            "section_code": "99",
            "capacity": "30",
            "evaluation_method": "absolute",
            "waitlist_capacity": "0",
            "org_unit": str(course.org_unit_id),
            "instruction_language": "",
        },
    )
    assert response.status_code == 302, response.content.decode()[:2000]
    created = Section.objects.get(section_code="99")
    assert created.status == SectionStatus.DRAFT

    response = client.post(
        f"/admin/offering/section/{created.pk}/change/",
        _change_data(
            created,
            [
                {
                    "weekday": str(taken.weekday),
                    "start_time": taken.start_time.strftime("%H:%M"),
                    "end_time": taken.end_time.strftime("%H:%M"),
                    "room": str(taken.room_id),
                }
            ],
        ),
    )
    assert response.status_code == 302, response.content.decode()[:3000]
    texts = [str(message) for message in get_messages(response.wsgi_request)]
    expected = f"The room is already booked at this time by {section.label()} ({section.term.code})."
    assert expected in texts
    assert created.meetings.count() == 0


def test_shows_a_room_timetable(manager: User, section: Section) -> None:
    taken = section.meetings.filter(room__isnull=False).first()
    response = signed_in(manager).get(
        "/admin/offering/timetables/", {"term": section.term_id, "mode": "room", "target": taken.room_id}
    )
    assert response.status_code == 200
    assert section.label() in response.content.decode()


def test_publishes_and_cancels_a_section_from_its_page(manager: User, section: Section) -> None:
    draft = SectionFactory(term=section.term, section_code="DR")
    client = signed_in(manager)
    assert client.get(f"/admin/offering/section/{draft.pk}/publish/").status_code == 302
    draft.refresh_from_db()
    assert draft.status == SectionStatus.PUBLISHED
    client.post(f"/admin/offering/section/{draft.pk}/cancel/", {"_form_submitted": "on", "reason": "Too few students"})
    draft.refresh_from_db()
    assert draft.status == SectionStatus.CANCELLED


def test_lets_students_browse_the_catalog_and_instructors_see_their_teaching(section: Section) -> None:
    student = User.objects.get(email="student@demo.test")
    draft = SectionFactory(term=section.term, section_code="DR")
    client = signed_in(student)

    response = client.get("/portal/catalog/", {"term": section.term_id})
    page = response.content.decode()
    assert response.status_code == 200
    assert draft.label() not in page
    response = client.get("/portal/catalog/", {"term": section.term_id, "q": section.course.code})
    assert section.label() in response.content.decode()
    assert client.get(f"/portal/sections/{section.pk}/").status_code == 200
    assert client.get(f"/portal/sections/{draft.pk}/").status_code == 404
    assert client.get(f"/portal/sections/{section.pk}/syllabus/").status_code == 403

    instructor = User.objects.get(email="instructor@demo.test")
    taught = Section.objects.taught_by(instructor.person_id).filter(term_id=section.term_id).first()
    client = signed_in(instructor)
    response = client.get("/portal/teaching/", {"term": section.term_id})
    assert response.status_code == 200
    assert taught.label() in response.content.decode()
    assert client.get(f"/portal/sections/{taught.pk}/syllabus/").status_code == 200


def test_instructors_write_and_publish_a_syllabus_in_the_portal(section: Section) -> None:
    instructor = User.objects.get(email="instructor@demo.test")
    taught = Section.objects.taught_by(instructor.person_id).filter(term_id=section.term_id).first()
    client = signed_in(instructor)
    url = f"/portal/sections/{taught.pk}/syllabus/"

    response = client.post(url, {"language": "en", "overview": "x", "add_assessment": "1"})
    assert response.status_code == 200
    assert response.content.decode().count('name="assessment_item"') >= 1

    response = client.post(
        url,
        {
            "language": "en",
            "overview": "Lists and trees",
            "published": "1",
            "assessment_item": ["Final exam"],
            "assessment_weight": ["60"],
            "week": ["1", "2"],
            "topic": ["Introduction", ""],
            "save": "1",
        },
    )
    assert response.status_code == 302
    taught.syllabus.refresh_from_db()
    assert taught.syllabus.published_at is not None
    assert taught.syllabus.content["weekly_plan"] == [{"week": 1, "topic": "Introduction"}]
    assert taught.syllabus.content["assessment"] == [{"item": "Final exam", "weight": 60}]

    response = client.post(url, {"language": "en", "week": ["99"], "topic": ["x"], "save": "1"})
    assert response.status_code == 422
