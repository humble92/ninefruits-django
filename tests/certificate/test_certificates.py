"""Certificates (original ``tests/Feature/Certificate/CertificateTest.php``): serial numbers per
prefix, the stored PDF and its checksum, the issue audit; audience, inactive kinds, holds,
permissions and missing templates; the public verification page with masked holder details,
revoked and expired codes, ``certificate_verify``; transcripts with finalized grades and
``certificate_render``; issuing from the student record page, the ledger, the holder's download
and portal list, revocation; and the database hiding other students' issues.

Gotenberg is answered by a fake (``conftest.gotenberg``); ``test_gotenberg_renders_a_real_pdf``
renders a real one when the service runs (marker ``gotenberg``)."""

from __future__ import annotations

import hashlib
import io
from datetime import date, timedelta
from typing import Any

import httpx
import pytest
from django.conf import settings
from django.core.exceptions import PermissionDenied, ValidationError
from django.core.management import call_command
from django.db import connection
from django.utils import timezone

from ninefruits.audit.models import ActivityLog
from ninefruits.certificate.enums import CertificateIssueStatus, VerificationReason
from ninefruits.certificate.models import CertificateIssue
from ninefruits.certificate.services import CertificateRenderer, CertificateVerification, mask_name, mask_number
from ninefruits.certificate.settings import CertificateSettings
from ninefruits.core.db import session_context
from ninefruits.i18n.translation import translate
from ninefruits.media.services import open_media
from ninefruits.registration.enums import HoldType
from ninefruits.registration.models import RegistrationHold
from ninefruits.security.enums import Permission
from tests.factories.offering import SectionFactory
from tests.factories.person import StudentRecordFactory
from tests.factories.registration import EnrollmentFactory
from tests.factories.security import UserFactory
from tests.factories.term import TermFactory

from .conftest import signed_in

pytestmark = pytest.mark.django_db

YEAR = timezone.now().year


def stored_bytes(issue: CertificateIssue) -> bytes:
    media = issue.pdf()
    assert media is not None
    with open_media(media) as handle:
        return bytes(handle.read())


def test_issues_with_sequential_serial_numbers_stores_the_pdf_and_records_an_audit_entry(
    kinds: dict[str, Any], officer: Any, record: Any, issue_certificate: Any, as_user: Any
) -> None:
    with as_user(officer):
        first = issue_certificate.handle(record, kinds["ENR"], "ko", officer, "장학금 신청", 2)
        second = issue_certificate.handle(record, kinds["ENR"], "en", officer)

    assert first.serial_number == f"ENR-{YEAR}-000001"
    assert second.serial_number == f"ENR-{YEAR}-000002"
    assert len(first.verification_code) == 20
    assert first.verification_code.isupper() or first.verification_code.isdigit()
    assert first.copies == 2
    assert first.status == CertificateIssueStatus.ISSUED
    assert first.issued_by_id == officer.pk
    assert len(first.pdf_checksum) == 64

    data = stored_bytes(first)
    assert data.startswith(b"%PDF")
    assert hashlib.sha256(data).hexdigest() == first.pdf_checksum
    media = first.pdf()
    assert media.file_name == f"ENR-{YEAR}-000001.pdf"
    assert media.mime_type == "application/pdf"
    assert media.sha256 == first.pdf_checksum
    entries = ActivityLog.objects.filter(event="certificate.issued")
    assert entries.count() == 2
    entry = entries.get(subject_id=first.pk)
    assert entry.properties == {
        "student_number": record.student_number,
        "type": "ENR",
        "locale": "ko",
        "serial": first.serial_number,
        "copies": 2,
    }

    # A graduation certificate for a graduate counts separately.
    graduate = StudentRecordFactory(graduated=True)
    with as_user(officer):
        assert issue_certificate.handle(graduate, kinds["GRD"], "en", officer).serial_number == f"GRD-{YEAR}-000001"


def test_follows_the_configured_serial_pattern(
    kinds: dict[str, Any], officer: Any, record: Any, issue_certificate: Any
) -> None:
    certificate_settings = CertificateSettings.load()
    certificate_settings.serial_pattern = "{YY}{TYPE}{SEQ:3}/C"
    certificate_settings.save()

    issue = issue_certificate.handle(record, kinds["ENR"], "en", officer)

    assert issue.serial_number == f"{str(YEAR)[-2:]}ENR001/C"
    assert issue.pdf().file_name == f"{str(YEAR)[-2:]}ENR001-C.pdf"


def test_enforces_the_audience_active_kinds_holds_templates_and_permissions(
    kinds: dict[str, Any], officer: Any, record: Any, issue_certificate: Any, as_user: Any
) -> None:
    enrollment, graduation = kinds["ENR"], kinds["GRD"]
    with pytest.raises(ValidationError):
        issue_certificate.handle(record, graduation, "ko", officer)

    graduate = StudentRecordFactory(graduated=True)
    with pytest.raises(ValidationError):
        issue_certificate.handle(graduate, enrollment, "ko", officer)

    enrollment.is_active = False
    enrollment.save()
    with pytest.raises(ValidationError, match="not issued any more"):
        issue_certificate.handle(record, enrollment, "ko", officer)
    enrollment.is_active = True
    enrollment.save()

    hold = RegistrationHold.objects.create(
        student_record=record,
        hold_type=HoldType.ADMINISTRATIVE,
        blocks_registration=False,
        blocks_certificates=True,
        starts_at=timezone.now() - timedelta(days=1),
        reason="Under investigation",
        created_by=officer,
    )
    # The hold blocks even when the issuer's own database access would not show it.
    with as_user(officer), pytest.raises(ValidationError, match="A hold blocks certificates"):
        issue_certificate.handle(record, enrollment, "ko", officer)
    hold.ends_at = timezone.now() - timedelta(minutes=1)
    hold.save()
    with as_user(officer):
        assert isinstance(issue_certificate.handle(record, enrollment, "ko", officer), CertificateIssue)

    clerk = UserFactory(permissions=[Permission.STUDENT_RECORDS_VIEW])
    with pytest.raises(PermissionDenied):
        issue_certificate.handle(record, enrollment, "ko", clerk)

    with pytest.raises(ValidationError, match='language "fr"'):
        issue_certificate.handle(record, enrollment, "fr", officer)
    # Refused issues leave nothing behind.
    assert CertificateIssue.objects.count() == 1


def test_issues_nothing_when_the_pdf_service_fails(
    kinds: dict[str, Any], officer: Any, record: Any, issue_certificate: Any, gotenberg: Any
) -> None:
    from ninefruits.pdf import PdfRenderingError

    gotenberg.mock(return_value=httpx.Response(503))
    with pytest.raises(PdfRenderingError):
        issue_certificate.handle(record, kinds["ENR"], "en", officer)
    assert not CertificateIssue.objects.exists()

    # The number was consumed: uniqueness over continuity (ADR 0013).
    gotenberg.mock(side_effect=lambda request: httpx.Response(200, content=b"%PDF-1.4\n%%EOF\n"))
    assert issue_certificate.handle(record, kinds["ENR"], "en", officer).serial_number == f"ENR-{YEAR}-000002"


def test_verifies_on_the_public_page_with_masked_holder_details_and_reports_revoked_and_expired(
    kinds: dict[str, Any], officer: Any, record: Any, issue_certificate: Any, as_user: Any
) -> None:
    issue = issue_certificate.handle(record, kinds["ENR"], "ko", officer)
    name = record.person.display_name("ko")
    client = signed_in(UserFactory())
    client.logout()

    page = client.get("/verify/")
    assert page.status_code == 200
    assert "Enter the verification code printed on the certificate" in page.content.decode()

    response = client.get(f"/verify/{issue.verification_code}/")
    content = response.content.decode()
    assert response.status_code == 200
    assert "This certificate was issued by the institution and is valid." in content
    assert issue.serial_number in content
    assert mask_name(name) in content
    assert mask_number(record.student_number) in content
    assert record.student_number not in content
    assert response["X-Robots-Tag"] == "noindex"
    # The form submits the code as a query parameter; codes are case insensitive.
    assert "is valid" in client.get(f"/verify/?code={issue.verification_code.lower()}").content.decode()
    assert "No certificate matches this code." in client.get("/verify/NOPE/").content.decode()

    out = io.StringIO()
    assert call_command("certificate_verify", issue.verification_code, stdout=out) == 0
    assert "Valid." in out.getvalue()
    assert issue.serial_number in out.getvalue()

    with as_user(officer):
        issue_certificate.revoke(issue, officer, "Wrong purpose")
    issue.refresh_from_db()
    assert issue.status == CertificateIssueStatus.REVOKED
    assert issue.revoked_at is not None
    assert issue.revoked_by_id == officer.pk
    assert ActivityLog.objects.filter(event="certificate.revoked", reason="Wrong purpose").exists()
    assert "This certificate has been revoked." in client.get(f"/verify/{issue.verification_code}/").content.decode()
    assert call_command("certificate_verify", issue.verification_code, stdout=io.StringIO(), stderr=io.StringIO()) == 2
    with pytest.raises(ValidationError):
        issue_certificate.revoke(issue, officer, "Again")
    # The row and the file stay.
    assert issue.pdf() is not None

    certificate_settings = CertificateSettings.load()
    certificate_settings.verification_valid_days = 30
    certificate_settings.save()
    old = issue_certificate.handle(record, kinds["ENR"], "ko", officer)
    CertificateIssue.objects.filter(pk=old.pk).update(issued_at=timezone.now() - timedelta(days=31))
    assert (
        "The verification period for this certificate has ended."
        in client.get(f"/verify/{old.verification_code}/").content.decode()
    )
    assert CertificateVerification().check(old.verification_code).reason == VerificationReason.EXPIRED


def test_revocation_needs_a_reason_and_the_issue_permission(
    kinds: dict[str, Any], officer: Any, record: Any, issue_certificate: Any
) -> None:
    issue = issue_certificate.handle(record, kinds["ENR"], "en", officer)
    with pytest.raises(ValidationError, match="Enter a reason"):
        issue_certificate.revoke(issue, officer, "  ")
    with pytest.raises(PermissionDenied):
        issue_certificate.revoke(issue, UserFactory(permissions=[Permission.CERTIFICATES_MANAGE]), "Mistake")
    issue.refresh_from_db()
    assert issue.status == CertificateIssueStatus.ISSUED


def test_verification_json_tells_only_what_the_paper_shows(
    kinds: dict[str, Any], officer: Any, record: Any, issue_certificate: Any
) -> None:
    issue = issue_certificate.handle(record, kinds["ENR"], "en", officer)
    data = CertificateVerification().check(issue.verification_code).as_dict()
    assert data["valid"] is True
    assert data["reason"] is None
    assert data["certificate"]["serial_number"] == issue.serial_number
    assert data["certificate"]["type"] == "ENR"
    assert data["certificate"]["type_name"] == "Certificate of Enrollment"
    assert data["certificate"]["student_number"] == mask_number(record.student_number)
    assert record.student_number not in str(data)
    assert CertificateVerification().check("x" * 41).as_dict() == {
        "valid": False,
        "reason": "unknown",
        "certificate": None,
    }


def test_masks_names_and_numbers_like_the_original() -> None:
    assert mask_name("홍길동") == "홍*동"
    assert mask_name("Ji") == "J*"
    assert mask_name("A") == "A"
    assert mask_name("") == ""
    assert mask_name("Minsu Kim") == "M*******m"
    assert mask_number("202600123") == "2026*****"
    assert mask_number("1234") == "1234"


def test_renders_a_transcript_with_the_finalized_grades_and_renders_again_by_command(
    kinds: dict[str, Any], officer: Any, record: Any, issue_certificate: Any, gotenberg: Any
) -> None:
    from ninefruits.setup.seeders.profiles.korean_university import seed_scale_45

    seed_scale_45(True)
    term = TermFactory(published=True, start_date=date(2025, 3, 1), end_date=date(2025, 6, 20))
    graded = EnrollmentFactory(student_record=record, section=SectionFactory(term=term, published=True), grade="A0")
    # A grade not finalized yet is not on the transcript.
    EnrollmentFactory(student_record=record, section=SectionFactory(term=term, published=True))

    issue = issue_certificate.handle(record, kinds["TRN"], "en", officer)
    content = CertificateRenderer().content(issue)
    assert len(content.terms) == 1
    assert [enrollment.pk for enrollment in content.terms[0].enrollments] == [graded.pk]
    assert content.paragraphs
    assert "<svg" in content.qr_svg
    assert content.verification_url == f"{settings.APP_URL.rstrip('/')}/verify/{issue.verification_code}/"
    html = gotenberg.calls.last.request.content.decode()
    assert graded.course.code in html
    assert "Academic Transcript" in html
    assert issue.serial_number in html

    checksum = issue.pdf_checksum
    err = io.StringIO()
    assert call_command("certificate_render", issue.serial_number, stdout=io.StringIO(), stderr=err) == 1
    assert "--reason is required." in err.getvalue()
    assert call_command("certificate_render", "NOPE", reason="x", stdout=io.StringIO(), stderr=io.StringIO()) == 1
    out = io.StringIO()
    assert call_command("certificate_render", issue.serial_number, reason="Template fixed", stdout=out) == 0
    issue.refresh_from_db()
    assert len(issue.pdf_checksum) == 64
    assert issue.pdf_checksum != checksum
    assert hashlib.sha256(stored_bytes(issue)).hexdigest() == issue.pdf_checksum
    assert issue.serial_number == f"TRN-{YEAR}-000001"
    assert CertificateIssue.objects.get(pk=issue.pk).pdf() is not None
    assert ActivityLog.objects.filter(event="certificate.rerendered").exists()
    command = ActivityLog.objects.filter(event="command.executed").latest("id")
    assert command.properties["command"] == "certificate_render"
    assert command.properties["result"] == {"serial": issue.serial_number, "checksum": issue.pdf_checksum}


def test_fills_placeholders_and_facts_in_the_template_language(
    kinds: dict[str, Any], officer: Any, issue_certificate: Any
) -> None:
    graduate = StudentRecordFactory(graduated=True, degree_number="D-2026-0001")
    graduate.person.name_variants = {"ko": "김민수"}
    graduate.person.save()
    issue = issue_certificate.handle(graduate, kinds["GRD"], "ko", officer, "취업")
    content = CertificateRenderer().content(issue)

    assert content.title == "졸업증명서"
    assert "학위번호: D-2026-0001" in content.paragraphs[-1]
    assert translate(graduate.program.name_translations, "ko") in content.paragraphs[0]
    assert content.facts["성명"] == "김민수"
    assert content.facts["학번"] == graduate.student_number
    assert "졸업일" in content.facts
    assert "학적 상태" not in content.facts
    assert content.signer == "교무처장"
    assert "년" in content.issued_on

    # Unknown placeholders stay as written; the settings signer is used without a template signer.
    template = kinds["ENR"].templates.get(locale="en")
    template.body = "{student_name} {unknown}\n\n\nSecond paragraph"
    template.signer = None
    template.save()
    certificate_settings = CertificateSettings.load()
    certificate_settings.signer = {"en": "President"}
    certificate_settings.save()
    record = StudentRecordFactory()
    issue = issue_certificate.handle(record, kinds["ENR"], "en", officer)
    content = CertificateRenderer().content(issue)
    assert content.paragraphs == [f"{record.person.display_name('en')} {{unknown}}", "Second paragraph"]
    assert content.signer == "President"
    assert content.facts["Year"] == "1"
    assert "Graduated" not in content.facts


def test_includes_the_photo_for_kinds_with_photos(
    kinds: dict[str, Any], officer: Any, record: Any, issue_certificate: Any
) -> None:
    from ninefruits.media.services import add_media_from_bytes

    png = (
        b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89"
        b"\x00\x00\x00\rIDATx\x9cc\xf8\x0f\x00\x00\x01\x01\x00\x05\x18\xd8N\x00\x00\x00\x00IEND\xaeB`\x82"
    )
    add_media_from_bytes(record.person, png, "photo.png", "photo")
    kind = kinds["ENR"]
    kind.has_photo = True
    kind.save()
    issue = issue_certificate.handle(record, kind, "en", officer)
    assert CertificateRenderer().content(issue).photo_data_uri.startswith("data:image/png;base64,")


def test_issues_from_the_student_record_page_lists_the_ledger_and_lets_the_holder_download(
    kinds: dict[str, Any], officer: Any, record: Any
) -> None:
    client = signed_in(officer)
    url = f"/admin/person/studentrecord/{record.pk}/issue-certificate/"
    assert client.get(url).status_code == 200
    response = client.post(url, {"certificate_type": kinds["ENR"].pk, "locale": "ko", "purpose": "Visa", "copies": 1})
    assert response.status_code == 302
    issue = CertificateIssue.objects.get()
    assert issue.purpose == "Visa"
    assert issue.locale == "ko"

    for page in [
        "/admin/certificate/certificateissue/",
        "/admin/certificate/certificateissue/?status=revoked",
        f"/admin/certificate/certificateissue/?type={kinds['ENR'].pk}&q={record.student_number}",
        f"/admin/certificate/certificateissue/{issue.pk}/change/",
        f"/admin/certificate/certificateissue/{issue.pk}/rerender/",
        f"/admin/certificate/certificateissue/{issue.pk}/revoke/",
        "/admin/certificate/certificatetype/",
        "/admin/certificate/certificatetype/add/",
        f"/admin/certificate/certificatetype/{kinds['ENR'].pk}/change/",
        "/admin/settings/certificates/",
        f"/admin/person/studentrecord/{record.pk}/change/",
    ]:
        assert client.get(page).status_code == 200, page
    assert issue.serial_number in client.get("/admin/certificate/certificateissue/").content.decode()

    student = UserFactory(person=record.person)
    holder = signed_in(student)
    download = holder.get(f"/certificates/{issue.pk}/download/")
    assert download.status_code == 200
    assert download["Content-Type"] == "application/pdf"
    assert download["X-Content-Type-Options"] == "nosniff"
    assert f'filename="{issue.serial_number}.pdf"' in download["Content-Disposition"]
    portal = holder.get("/portal/certificates/").content.decode()
    assert issue.serial_number in portal
    assert "재학증명서" in portal  # the kind's name in the issue's language

    response = client.post(f"/admin/certificate/certificateissue/{issue.pk}/revoke/", {"reason": "Mistake"})
    assert response.status_code == 302
    issue.refresh_from_db()
    assert issue.status == CertificateIssueStatus.REVOKED
    assert issue.revocation_reason == "Mistake"

    # Staff keep the file for the record; the holder cannot download a revoked certificate.
    assert client.get(f"/certificates/{issue.pk}/download/").status_code == 200
    assert holder.get(f"/certificates/{issue.pk}/download/").status_code == 403
    assert issue.serial_number in holder.get("/portal/certificates/").content.decode()

    other = signed_in(UserFactory(person=StudentRecordFactory().person))
    assert other.get(f"/certificates/{issue.pk}/download/").status_code == 404
    assert issue.serial_number not in other.get("/portal/certificates/").content.decode()


def test_re_renders_from_the_ledger_and_refuses_revoked_issues(
    kinds: dict[str, Any], officer: Any, record: Any, issue_certificate: Any
) -> None:
    issue = issue_certificate.handle(record, kinds["ENR"], "en", officer)
    checksum = issue.pdf_checksum
    client = signed_in(officer)
    assert client.post(f"/admin/certificate/certificateissue/{issue.pk}/rerender/", {}).status_code == 302
    issue.refresh_from_db()
    assert issue.pdf_checksum != checksum
    assert len(issue.get_media(CertificateIssue.PDF_COLLECTION)) == 1

    issue_certificate.revoke(issue, officer, "Wrong")
    assert client.get(f"/admin/certificate/certificateissue/{issue.pk}/rerender/").status_code == 403


def test_the_issue_screen_shows_action_errors(kinds: dict[str, Any], officer: Any) -> None:
    graduate = StudentRecordFactory(graduated=True)
    client = signed_in(officer)
    response = client.post(
        f"/admin/person/studentrecord/{graduate.pk}/issue-certificate/",
        {"certificate_type": kinds["ENR"].pk, "locale": "en", "copies": 1},
    )
    assert response.status_code == 200
    assert "This certificate is only for" in response.content.decode()
    assert not CertificateIssue.objects.exists()


def test_staff_without_the_issue_permission_see_no_issue_button(kinds: dict[str, Any], record: Any) -> None:
    clerk = UserFactory(permissions=[Permission.ADMIN_PANEL_ACCESS, Permission.STUDENT_RECORDS_VIEW])
    client = signed_in(clerk)
    assert "issue-certificate" not in client.get(f"/admin/person/studentrecord/{record.pk}/change/").content.decode()
    assert client.get(f"/admin/person/studentrecord/{record.pk}/issue-certificate/").status_code == 403
    assert client.get("/admin/certificate/certificateissue/").status_code == 403


def test_hides_other_students_issues_at_the_database_level(
    kinds: dict[str, Any], officer: Any, record: Any, issue_certificate: Any, without_baseline: None
) -> None:
    session_context().for_system("test")
    issue = issue_certificate.handle(record, kinds["ENR"], "ko", officer)
    other = UserFactory(person=StudentRecordFactory().person)
    holder = UserFactory(person=record.person)
    context = session_context()

    context.for_user(other.pk)
    assert CertificateIssue.objects.count() == 0

    context.for_user(holder.pk)
    assert CertificateIssue.objects.filter(pk=issue.pk).exists()
    # RLS filters the row from the update: nothing changes, no error.
    assert CertificateIssue.objects.filter(pk=issue.pk).update(purpose="hacked") == 0
    with connection.cursor() as cursor:
        cursor.execute("UPDATE certificate_issues SET status = 'revoked', revoked_at = now() WHERE id = %s", [issue.pk])
        assert cursor.rowcount == 0
    context.for_system("test")
    issue.refresh_from_db()
    assert issue.purpose is None
    assert issue.status == CertificateIssueStatus.ISSUED


@pytest.mark.gotenberg
def test_gotenberg_renders_a_real_pdf(kinds: dict[str, Any], officer: Any, record: Any, issue_certificate: Any) -> None:
    try:
        httpx.get(f"{settings.GOTENBERG_URL.rstrip('/')}/health", timeout=2).raise_for_status()
    except httpx.HTTPError:
        pytest.skip("Gotenberg is not reachable.")

    for locale in ("ko", "zh-hans", "lo"):
        issue = issue_certificate.handle(record, kinds["ENR"], locale, officer, "Test")
        data = stored_bytes(issue)
        assert data.startswith(b"%PDF")
        assert hashlib.sha256(data).hexdigest() == issue.pdf_checksum
    assert b"NotoSansLao" in data
