"""Certificate screens on the tiny demo (the Phase 8 datasets of the original
``tests/Feature/Admin/AdminPagesTest.php`` and the screen parts of ``CertificateTest.php``): the
demo issues (one revoked, PDFs stored), every certificate page for an administrator and the demo
certificate officer, the Korean screens, the portal list of the demo student, the settings page,
editing a kind's templates, and the rate limit of the verification page."""

from __future__ import annotations

from collections.abc import Iterator

import pytest
from django.core.cache import cache

from ninefruits.certificate.enums import CertificateIssueStatus
from ninefruits.certificate.models import CertificateIssue, CertificateTemplate, CertificateType
from ninefruits.certificate.settings import CertificateSettings
from ninefruits.security.enums import Permission
from ninefruits.security.models import User
from ninefruits.setup.seeders.demo import DemoOptions, use_options
from ninefruits.setup.seeders.demo.accounts import DemoAccountSeeder
from ninefruits.setup.seeders.demo.certificate import DemoCertificateSeeder
from ninefruits.setup.seeders.demo.curriculum import DemoCurriculumSeeder
from ninefruits.setup.seeders.demo.grading import DemoGradeHistorySeeder
from ninefruits.setup.seeders.demo.people import DemoPeopleSeeder
from ninefruits.setup.seeders.demo.reference import DemoReferenceSeeder
from ninefruits.setup.seeders.demo.registration import DemoRegistrationSeeder
from tests.factories.security import UserFactory

from .conftest import signed_in

pytestmark = pytest.mark.django_db


@pytest.fixture
def demo(essential_data: None) -> Iterator[None]:
    with use_options(DemoOptions(size="tiny", seed=42)):
        for seeder in (
            DemoAccountSeeder,
            DemoReferenceSeeder,
            DemoPeopleSeeder,
            DemoCurriculumSeeder,
            DemoGradeHistorySeeder,
            DemoRegistrationSeeder,
            DemoCertificateSeeder,
        ):
            seeder()()
    yield


@pytest.fixture
def manager() -> User:
    return UserFactory(permissions=list(Permission))


def test_seeds_demo_issues_and_renders_every_certificate_page(demo: None, manager: User) -> None:
    issues = list(CertificateIssue.objects.select_related("certificate_type").order_by("pk"))
    assert {issue.certificate_type.code for issue in issues} == {"ENR", "GRD", "TRN"}
    assert sum(issue.status == CertificateIssueStatus.REVOKED for issue in issues) == 1
    assert all(issue.pdf() is not None and len(issue.pdf_checksum or "") == 64 for issue in issues)
    assert CertificateTemplate.objects.count() == 12

    issue = issues[0]
    kind = CertificateType.objects.get(code="TRN")
    pages = [
        "/admin/certificate/certificateissue/",
        "/admin/certificate/certificateissue/?status=issued",
        f"/admin/certificate/certificateissue/?type={kind.pk}",
        "/admin/certificate/certificateissue/?q=ENR",
        f"/admin/certificate/certificateissue/{issue.pk}/change/",
        f"/admin/certificate/certificateissue/{issue.pk}/rerender/",
        f"/admin/certificate/certificateissue/{issue.pk}/revoke/",
        "/admin/certificate/certificatetype/",
        "/admin/certificate/certificatetype/add/",
        f"/admin/certificate/certificatetype/{kind.pk}/change/",
        "/admin/settings/certificates/",
        f"/admin/person/studentrecord/{issue.student_record_id}/change/",
        f"/admin/person/studentrecord/{issue.student_record_id}/issue-certificate/",
        f"/certificates/{issue.pk}/download/",
        f"/verify/{issue.verification_code}/",
    ]
    client = signed_in(manager)
    for page in pages:
        assert client.get(page).status_code == 200, page

    officer = User.objects.get(email="certificate-officer@demo.test")
    client = signed_in(officer)
    for page in pages[:7] + pages[11:]:
        assert client.get(page).status_code == 200, page
    # The certificate officer issues but does not manage kinds or settings.
    assert client.get("/admin/settings/certificates/").status_code == 403


def test_the_demo_student_sees_their_certificates_in_the_portal(demo: None) -> None:
    student = User.objects.get(email="student@demo.test")
    issue = CertificateIssue.objects.filter(student_record__person=student.person).first()
    assert issue is not None
    client = signed_in(student)
    page = client.get("/portal/certificates/").content.decode()
    assert issue.serial_number in page
    assert 'href="/portal/certificates/"' in client.get("/portal/").content.decode()
    assert client.get(f"/certificates/{issue.pk}/download/").status_code == 200


def test_renders_the_certificate_pages_in_korean(demo: None, manager: User) -> None:
    manager.locale = "ko"
    manager.save(update_fields=["locale"])
    client = signed_in(manager)
    assert "발급 대장" in client.get("/admin/certificate/certificateissue/").content.decode()
    assert "증명서 설정" in client.get("/admin/settings/certificates/").content.decode()


def test_saves_the_certificate_settings(kinds: dict[str, CertificateType], manager: User) -> None:
    client = signed_in(manager)
    url = "/admin/settings/certificates/"
    response = client.post(
        url,
        {
            "serial_pattern": "{TYPE}{SEQ:5}",
            "verification_valid_days": 365,
            "signer_en": " President ",
            "signer_ko": "",
        },
    )
    assert response.status_code == 302
    saved = CertificateSettings.load()
    assert saved.serial_pattern == "{TYPE}{SEQ:5}"
    assert saved.verification_valid_days == 365
    assert saved.signer == {"en": "President"}
    assert 'value="President"' in client.get(url).content.decode()

    for pattern in ("{TYPE}-{YYYY}", "{SEQ:6}{TYPE}", "{MONTH}{SEQ:6}"):
        response = client.post(url, {"serial_pattern": pattern, "verification_valid_days": 0})
        assert response.status_code == 422, pattern
    assert CertificateSettings.load().serial_pattern == "{TYPE}{SEQ:5}"


def test_edits_a_kind_and_its_templates(kinds: dict[str, CertificateType], manager: User) -> None:
    kind = kinds["ENR"]
    templates = list(kind.templates.order_by("locale"))
    client = signed_in(manager)
    data = {
        "code": kind.code,
        "audience": kind.audience,
        "name__en": "Enrollment certificate",
        "name__ko": "재학증명서",
        "is_active": "on",
        "sort_order": 10,
        "templates-TOTAL_FORMS": len(templates) + 1,
        "templates-INITIAL_FORMS": len(templates),
        "templates-MIN_NUM_FORMS": 0,
        "templates-MAX_NUM_FORMS": 1000,
    }
    for index, template in enumerate(templates):
        data |= {
            f"templates-{index}-id": template.pk,
            f"templates-{index}-certificate_type": kind.pk,
            f"templates-{index}-locale": template.locale,
            f"templates-{index}-title": template.title,
            f"templates-{index}-body": template.body,
            f"templates-{index}-footer": template.footer or "",
            f"templates-{index}-signer": template.signer or "",
        }
    # The Lao template exists: adding another one for Lao is refused.
    new = len(templates)
    data |= {
        f"templates-{new}-certificate_type": kind.pk,
        f"templates-{new}-locale": "lo",
        f"templates-{new}-title": "Again",
        f"templates-{new}-body": "Again",
    }
    response = client.post(f"/admin/certificate/certificatetype/{kind.pk}/change/", data)
    assert response.status_code == 200
    assert kind.templates.count() == 4

    data[f"templates-{new}-locale"] = ""
    data["templates-TOTAL_FORMS"] = len(templates)
    data[f"templates-{templates.index(next(t for t in templates if t.locale == 'en'))}-title"] = "Proof of enrollment"
    response = client.post(f"/admin/certificate/certificatetype/{kind.pk}/change/", data)
    assert response.status_code == 302
    kind.refresh_from_db()
    assert kind.name_translations["en"] == "Enrollment certificate"
    assert kind.templates.get(locale="en").title == "Proof of enrollment"


def test_limits_the_verification_page_to_30_requests_a_minute(kinds: dict[str, CertificateType]) -> None:
    cache.clear()
    client = signed_in(UserFactory())
    client.logout()
    statuses = [client.get("/verify/UNKNOWN0000/").status_code for _ in range(31)]
    assert statuses[:30] == [200] * 30
    assert statuses[30] == 429
