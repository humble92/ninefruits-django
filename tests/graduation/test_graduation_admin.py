"""Graduation and report screens on the tiny demo (the Phase 11 datasets in the style of the
original ``tests/Feature/Admin/AdminPagesTest.php``, and ``DemoGraduationSeeder``): the seeder
running once, the degree audit and waiver lists, a stored audit, the student record buttons, the
graduation settings page, every standard report on screen and as CSV, and the student's portal
page, in English and Korean."""

from __future__ import annotations

from collections.abc import Iterator

import pytest
from django.test import Client

from ninefruits.audit.models import ActivityLog
from ninefruits.core.db import session_context
from ninefruits.graduation.models import DegreeAudit, DegreeRequirementWaiver
from ninefruits.graduation.settings import GraduationSettings
from ninefruits.person.models import StudentRecord
from ninefruits.reporting.services import REPORTS
from ninefruits.security.models import User
from ninefruits.setup.seeders.demo import DemoOptions, use_options
from ninefruits.setup.seeders.demo.accounts import DemoAccountSeeder
from ninefruits.setup.seeders.demo.assessment import DemoAssessmentSeeder
from ninefruits.setup.seeders.demo.curriculum import DemoCurriculumSeeder
from ninefruits.setup.seeders.demo.grading import DemoGradeHistorySeeder, DemoGradingSeeder
from ninefruits.setup.seeders.demo.graduation import DemoGraduationSeeder
from ninefruits.setup.seeders.demo.people import DemoPeopleSeeder
from ninefruits.setup.seeders.demo.reference import DemoReferenceSeeder
from ninefruits.setup.seeders.demo.registration import DemoRegistrationSeeder
from ninefruits.term.models import Term

pytestmark = pytest.mark.django_db

HEADINGS = {
    "en": ("Degree audits", "Requirement waivers", "Reports", "Graduation requirements"),
    "ko": ("졸업 요건 점검", "요건 면제", "보고서", "졸업 요건"),
}


@pytest.fixture(autouse=True)
def demo(essential_data: None) -> Iterator[None]:
    from ninefruits.setup.seeders.profiles.korean_university import KoreanUniversityProfileSeeder

    KoreanUniversityProfileSeeder()()
    with use_options(DemoOptions(size="tiny", seed=42)):
        for seeder in (
            DemoAccountSeeder,
            DemoReferenceSeeder,
            DemoPeopleSeeder,
            DemoCurriculumSeeder,
            DemoGradeHistorySeeder,
            DemoRegistrationSeeder,
            DemoGradingSeeder,
            DemoAssessmentSeeder,
            DemoGraduationSeeder,
        ):
            seeder()()
    yield


def signed_in(email: str, language: str | None = None) -> Client:
    client = Client(headers={"accept-language": language} if language else {})
    client.force_login(User.objects.get(email=email))
    session_context().reset()
    return client


def test_seeds_audits_once() -> None:
    audits = DegreeAudit.objects.count()
    assert audits > 0
    assert DegreeAudit.objects.filter(term__isnull=False).count() == audits
    assert ActivityLog.objects.filter(event="graduation.audits_run").exists()
    waivers = DegreeRequirementWaiver.objects.count()

    with use_options(DemoOptions(size="tiny", seed=42)):
        DemoGraduationSeeder()()
    assert DegreeAudit.objects.count() == audits
    assert DegreeRequirementWaiver.objects.count() == waivers


@pytest.mark.parametrize("language", ["en", "ko"])
def test_renders_the_graduation_and_report_screens(language: str) -> None:
    audits_heading, waivers_heading, reports_heading, portal_heading = HEADINGS[language]
    client = signed_in("registrar@demo.test", language)

    listing = client.get("/admin/graduation/degreeaudit/")
    assert listing.status_code == 200
    assert audits_heading in listing.content.decode()
    assert client.get("/admin/graduation/degreeaudit/", {"satisfied": "no", "record_status": "all"}).status_code == 200
    assert client.get("/admin/graduation/degreeaudit/run/").status_code == 200
    audit = DegreeAudit.objects.newest_per_student().first()
    assert audit is not None
    assert client.get(f"/admin/graduation/degreeaudit/{audit.pk}/open/").status_code == 200
    assert client.get(f"/admin/graduation/degreeaudit/{audit.pk}/change/").status_code == 200
    assert client.get(f"/admin/graduation/degreeaudit/{audit.pk}/rerun/").status_code == 200

    waivers = client.get("/admin/graduation/degreerequirementwaiver/", {"status": "all"})
    assert waivers.status_code == 200
    assert waivers_heading in waivers.content.decode()

    record = StudentRecord.objects.filter(status="enrolled").order_by("student_number").first()
    assert record is not None
    assert client.get(f"/admin/person/studentrecord/{record.pk}/change/").status_code == 200
    assert client.get(f"/admin/person/studentrecord/{record.pk}/degree-audit/").status_code == 200
    assert client.get(f"/admin/person/studentrecord/{record.pk}/waive-requirement/").status_code == 200
    assert client.get("/admin/settings/graduation/").status_code == 200

    term = Term.objects.order_by("-start_date").first()
    for key, definition in REPORTS.items():
        params = {"report": key, **({"term": term.pk} if "term" in definition.params else {})}
        page = client.get("/admin/reports/", params)
        assert page.status_code == 200, key
        assert reports_heading in page.content.decode()
        csv = client.get(f"/reports/{key}.csv", {k: v for k, v in params.items() if k != "report"})
        assert csv.status_code == 200, key

    portal = signed_in("student@demo.test", language).get("/portal/graduation/")
    assert portal.status_code == 200
    assert portal_heading in portal.content.decode()


def test_saves_the_graduation_settings() -> None:
    client = signed_in("registrar@demo.test")
    bad = client.post(
        "/admin/settings/graduation/", {"degree_number_pattern": "{PROGRAM}-{YYYY}", "minimum_cumulative_gpa": "2"}
    )
    assert bad.status_code == 422
    good = client.post(
        "/admin/settings/graduation/", {"degree_number_pattern": "D-{YY}-{SEQ:4}", "minimum_cumulative_gpa": ""}
    )
    assert good.status_code == 302
    settings = GraduationSettings.load()
    assert settings.degree_number_pattern == "D-{YY}-{SEQ:4}"
    assert settings.minimum_cumulative_gpa is None
    assert ActivityLog.objects.filter(event="settings.updated", properties__group="graduation").exists()
    assert signed_in("department-assistant@demo.test").get("/admin/settings/graduation/").status_code == 403
