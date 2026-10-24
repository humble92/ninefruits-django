"""API v1 (porting-plan 12; no original test, the original had no API): authentication (session,
knox tokens issued and revoked with the audit), catalog permissions, throttles per scope, the
schema and Swagger UI for administrators only, health, certificate verification JSON, and the
LMS platform callbacks."""

from __future__ import annotations

import io
from datetime import timedelta
from typing import Any

import pytest
from django.core.management import call_command
from django.utils import timezone
from knox.models import AuthToken
from rest_framework.test import APIClient

from ninefruits.api.throttling import AnonThrottle, IntegrationThrottle, UserThrottle
from ninefruits.audit.models import ActivityLog
from ninefruits.lms.actions import PullGrades, SyncSection
from ninefruits.lms.enums import LinkStatus, SyncOperation, SyncStatus
from ninefruits.lms.models import LmsCourseLink, LmsPlatform, LmsSyncLog, LmsUserLink
from ninefruits.offering.models import SectionInstructor
from ninefruits.security.enums import Permission
from tests.factories.certificate import CertificateIssueFactory
from tests.factories.offering import SectionFactory
from tests.factories.person import InstructorFactory, StudentRecordFactory
from tests.factories.registration import EnrollmentFactory
from tests.factories.security import UserFactory

from .conftest import issue, session_client, token_client

pytestmark = pytest.mark.django_db


# -- authentication ---------------------------------------------------------------------------------
def test_tokens_are_issued_through_the_session_used_and_revoked_with_the_audit() -> None:
    user = UserFactory(permissions=[Permission.LMS_MANAGE])
    assert APIClient().get("/api/v1/me/").status_code == 401
    assert APIClient().get("/api/v1/me/")["WWW-Authenticate"] == "Token"

    session = session_client(user)
    me = session.get("/api/v1/me/").json()
    assert me["authentication"] == "session" and me["email"] == user.email
    assert me["permissions"] == ["lms.manage"]

    response = session.post("/api/v1/auth/tokens/", {"days": 30, "note": "Moodle"}, format="json")
    assert response.status_code == 201
    issued = response.json()
    token = issued["token"]
    assert token.startswith(issued["key"]) and len(issued["key"]) == 15
    stored = AuthToken.objects.get(user=user)
    assert stored.digest != token and token not in stored.digest
    entry = ActivityLog.objects.get(event="api.token_issued")
    assert entry.properties["key_prefix"] == issued["key"]
    assert token not in str(entry.properties)

    client = token_client(token)
    me = client.get("/api/v1/me/").json()
    assert me["authentication"] == "token" and me["token"]["key"] == issued["key"]
    assert client.get("/api/v1/auth/tokens/").json()["tokens"][0]["key"] == issued["key"]
    # A token cannot issue another token: a full sign-in is needed.
    assert client.post("/api/v1/auth/tokens/", {}, format="json").status_code == 403
    assert session.delete("/api/v1/auth/tokens/current/").status_code == 400

    assert client.delete("/api/v1/auth/tokens/current/").status_code == 204
    assert ActivityLog.objects.get(event="api.token_revoked").properties["key_prefixes"] == [issued["key"]]
    assert client.get("/api/v1/me/").status_code == 401
    assert session.delete(f"/api/v1/auth/tokens/{issued['key']}/").status_code == 404


def test_token_issue_needs_csrf_through_the_session_and_validates_the_lifetime() -> None:
    user = UserFactory()
    browser = APIClient(enforce_csrf_checks=True)
    browser.force_login(user)
    assert browser.post("/api/v1/auth/tokens/", {}, format="json").status_code == 403
    session = session_client(user)
    assert session.post("/api/v1/auth/tokens/", {"days": 400}, format="json").status_code == 400
    assert session.post("/api/v1/auth/tokens/", {}, format="json").status_code == 201
    # Default lifetime (REST_KNOX TOKEN_TTL, 90 days).
    expiry = AuthToken.objects.get(user=user).expiry
    assert timedelta(days=89) < expiry - timezone.now() <= timedelta(days=90)


def test_expired_tokens_and_inactive_accounts_are_refused() -> None:
    user = UserFactory()
    token = issue(user, days=1)
    AuthToken.objects.filter(user=user).update(expiry=timezone.now() - timedelta(minutes=1))
    assert token_client(token).get("/api/v1/me/").status_code == 401
    assert not AuthToken.objects.filter(user=user).exists()

    token = issue(user)
    user.is_active = False
    user.save()
    assert token_client(token).get("/api/v1/me/").status_code == 401
    assert token_client("nonsense-token").get("/api/v1/me/").status_code == 401


def test_issue_and_revoke_commands() -> None:
    admin = UserFactory(email="admin@example.test")
    service = UserFactory(email="moodle@example.test", permissions=[Permission.LMS_MANAGE])
    out = io.StringIO()
    code = call_command(
        "api_issue_token", "moodle@example.test", "--days=30", "--reason=Moodle", f"--actor={admin.email}", stdout=out
    )
    assert code == 0
    token = out.getvalue().splitlines()[0]
    assert token_client(token).get("/api/v1/lms/platforms/").status_code == 200
    command = ActivityLog.objects.filter(event="command.executed").order_by("-id").first()
    assert command.properties["command"] == "api_issue_token" and token not in str(command.properties)
    assert ActivityLog.objects.get(event="api.token_issued").causer_id == admin.pk

    assert call_command("api_issue_token", "nobody@example.test", stdout=io.StringIO(), stderr=io.StringIO()) == 1
    assert call_command("api_issue_token", service.email, "--days=0", stdout=io.StringIO(), stderr=io.StringIO()) == 1
    listing = io.StringIO()
    assert call_command("api_revoke_tokens", service.email, "--list", stdout=listing) == 0
    assert token[:15] in listing.getvalue()
    assert (
        call_command("api_revoke_tokens", service.email, "--key=nope", stdout=io.StringIO(), stderr=io.StringIO()) == 1
    )
    out = io.StringIO()
    assert call_command("api_revoke_tokens", service.email, "--reason=Rotated", stdout=out) == 0
    assert "1 token(s) revoked." in out.getvalue()
    assert token_client(token).get("/api/v1/me/").status_code == 401


# -- permissions --------------------------------------------------------------------------------------
def test_lms_and_report_endpoints_need_their_catalog_permissions() -> None:
    LmsPlatform.objects.create(code="TEST", name={"en": "Test"}, credentials={"token": "s3cr3t"}, options={})
    nobody = token_client(issue(UserFactory()))
    lms = token_client(issue(UserFactory(permissions=[Permission.LMS_MANAGE])))
    reports = token_client(issue(UserFactory(permissions=[Permission.REPORTS_VIEW])))

    assert nobody.get("/api/v1/lms/platforms/").status_code == 403
    assert reports.get("/api/v1/lms/platforms/").status_code == 403
    response = lms.get("/api/v1/lms/platforms/")
    assert response.status_code == 200
    assert response.json()[0]["code"] == "TEST"
    assert "s3cr3t" not in response.content.decode() and "credentials" not in response.json()[0]
    assert lms.get("/api/v1/lms/platforms/TEST/").json()["name"] == {"en": "Test"}
    assert lms.get("/api/v1/lms/platforms/NOPE/").status_code == 404

    assert nobody.get("/api/v1/reports/").status_code == 403
    assert lms.get("/api/v1/reports/").status_code == 403
    views = reports.get("/api/v1/reports/").json()["views"]
    assert {view["name"] for view in views} == {
        "students",
        "headcount",
        "term_records",
        "course_grades",
        "section_enrollments",
        "section_meetings",
        "status_changes",
        "degree_audits",
    }
    assert reports.get("/api/v1/reports/nope/").status_code == 404


def test_report_reads_follow_row_level_security_and_are_recorded(essential_data: None) -> None:
    from ninefruits.audit.models import SecurityEvent
    from ninefruits.reporting.models import ReportStudent

    records = StudentRecordFactory.create_batch(3)
    reader = UserFactory(permissions=[Permission.REPORTS_VIEW, Permission.STUDENT_RECORDS_VIEW])
    blind = UserFactory(permissions=[Permission.REPORTS_VIEW])

    rows = token_client(issue(reader)).get("/api/v1/reports/students/?limit=2").json()
    assert rows["count"] == 3 and len(rows["results"]) == 2
    assert set(rows["results"][0]) >= {"student_record_id", "student_number", "person_id", "program_name"}
    number = records[1].student_number
    filtered = token_client(issue(reader)).get(f"/api/v1/reports/students/?student_number={number}").json()
    assert [row["student_record_id"] for row in filtered["results"]] == [records[1].pk]
    assert token_client(issue(reader)).get("/api/v1/reports/students/?name_variants=x").status_code == 400
    assert token_client(issue(reader)).get("/api/v1/reports/students/?year_level=abc").status_code == 400

    # Without student_records.view the database shows no rows, and the application agrees.
    assert token_client(issue(blind)).get("/api/v1/reports/students/").json()["count"] == 0
    assert ReportStudent.objects.visible_to(blind).count() == 0
    event = SecurityEvent.objects.filter(type="data.exported").order_by("-id").first()
    assert event.properties["view"] == "students" and event.properties["source"] == "api"
    assert event.user_id == blind.pk

    headcount = token_client(issue(reader)).get("/api/v1/reports/headcount/").json()
    assert sum(row["students"] for row in headcount["results"]) == 3


# -- throttles ----------------------------------------------------------------------------------------
@pytest.fixture
def low_rates(monkeypatch: pytest.MonkeyPatch) -> None:
    rates = {"anon": "2/min", "user": "3/min", "integration": "4/min"}
    for throttle in (AnonThrottle, UserThrottle, IntegrationThrottle):
        monkeypatch.setattr(throttle, "THROTTLE_RATES", rates)


def test_throttles_count_anonymous_users_and_tokens_apart(low_rates: None) -> None:
    anonymous = APIClient()
    assert [anonymous.get("/api/v1/health/").status_code for _ in range(3)][-1] == 429

    user = UserFactory()
    session = session_client(user)
    codes = [session.get("/api/v1/me/").status_code for _ in range(4)]
    assert codes == [200, 200, 200, 429]

    # The same user's token has its own (higher) integration rate.
    client = token_client(issue(user))
    codes = [client.get("/api/v1/me/").status_code for _ in range(5)]
    assert codes == [200, 200, 200, 200, 429]
    assert "Retry-After" in client.get("/api/v1/me/")


# -- schema and docs ------------------------------------------------------------------------------------
def test_schema_needs_a_sign_in_and_swagger_ui_an_administrator() -> None:
    assert APIClient().get("/api/schema/").status_code == 401
    user = session_client(UserFactory())
    schema = user.get("/api/schema/?format=json")
    assert schema.status_code == 200
    paths = schema.json()["paths"]
    assert "/api/v1/lms/platforms/{code}/scores/" in paths and "/api/v1/reports/{name}/" in paths
    assert user.get("/api/docs/").status_code == 403

    admin = session_client(UserFactory(permissions=[Permission.ADMIN_PANEL_ACCESS]))
    page = admin.get("/api/docs/")
    assert page.status_code == 200
    html = page.content.decode()
    # Served from this site (sidecar), no third-party scripts (CSP).
    assert "swagger-ui-bundle.js" in html and "cdn.jsdelivr" not in html
    script = admin.get("/api/docs/?script=")
    assert script.status_code == 200 and "SwaggerUIBundle" in script.content.decode()


# -- health and verification ------------------------------------------------------------------------------
def test_health_tells_anonymous_callers_only_the_status() -> None:
    body = APIClient().get("/api/v1/health/").json()
    assert body == {"status": "degraded"}  # no scheduler heartbeat in tests

    from django.core.cache import cache

    from ninefruits.core.tasks import HEARTBEAT_CACHE_KEY

    cache.set(HEARTBEAT_CACHE_KEY, timezone.now().isoformat(), 600)
    assert APIClient().get("/api/v1/health/").json() == {"status": "ok"}
    admin = session_client(UserFactory(permissions=[Permission.ADMIN_PANEL_ACCESS]))
    assert admin.get("/api/v1/health/").json() == {
        "status": "ok",
        "checks": {"database": "ok", "cache": "ok", "scheduler": "ok"},
    }


def test_certificate_verification_json(essential_data: None) -> None:
    issued = CertificateIssueFactory()
    revoked = CertificateIssueFactory(revoked=True)
    client = APIClient()
    body = client.get(f"/api/v1/certificates/verify/{issued.verification_code}/").json()
    assert body["valid"] is True and body["reason"] is None
    assert body["certificate"]["serial_number"] == issued.serial_number
    assert body["certificate"]["holder"] != issued.student_record.person.display_name(issued.locale)
    assert body["certificate"]["student_number"].endswith("*")
    body = client.get(f"/api/v1/certificates/verify/{revoked.verification_code.lower()}/").json()
    assert body["valid"] is False and body["reason"] == "revoked"
    assert client.get("/api/v1/certificates/verify/NOPE/").json() == {
        "valid": False,
        "reason": "unknown",
        "certificate": None,
    }


# -- LMS callbacks -----------------------------------------------------------------------------------------
@pytest.fixture
def linked(essential_data: None) -> dict[str, Any]:
    from ninefruits.setup.seeders.profiles.korean_university import seed_scale_45

    seed_scale_45(True)
    platform = LmsPlatform.objects.create(
        code="TEST",
        name={"en": "Test LMS"},
        base_url="https://lms.test",
        options={},
        is_active=True,
        should_pull_grades=True,
    )
    section = SectionFactory(published=True)
    instructor = InstructorFactory()
    SectionInstructor.objects.create(section=section, instructor=instructor, role="primary")
    teacher = UserFactory(person=instructor.person)
    enrollment = EnrollmentFactory(section=section)
    student = UserFactory(person=enrollment.student_record.person)
    SyncSection().handle(platform, section)
    service = UserFactory(permissions=[Permission.LMS_MANAGE])
    return {
        "platform": platform,
        "section": section,
        "teacher": teacher,
        "enrollment": enrollment,
        "student": student,
        "client": token_client(issue(service)),
    }


def test_platform_reports_sync_results_and_course_links(linked: dict[str, Any]) -> None:
    client: APIClient = linked["client"]
    section = linked["section"]
    links = client.get("/api/v1/lms/platforms/TEST/course-links/?status=linked").json()
    assert links["count"] == 1 and links["results"][0]["external_course_id"] == f"course-{section.pk}"
    assert client.get("/api/v1/lms/platforms/TEST/course-links/?status=failed").json()["count"] == 0

    queued = LmsSyncLog.objects.create(
        platform=linked["platform"],
        section=section,
        operation=SyncOperation.ENROLLMENT_ADD,
        status=SyncStatus.QUEUED,
        started_at=timezone.now(),
    )
    url = "/api/v1/lms/platforms/TEST/sync-results/"
    response = client.post(
        url, {"log_id": queued.pk, "operation": "enrollment.add", "status": "succeeded", "message": "ok"}, format="json"
    )
    assert response.status_code == 201 and response.json() == {"log_id": queued.pk, "status": "succeeded"}
    queued.refresh_from_db()
    assert queued.status == SyncStatus.SUCCEEDED and queued.finished_at is not None
    again = client.post(url, {"log_id": queued.pk, "operation": "enrollment.add", "status": "failed"}, format="json")
    assert again.status_code == 400 and "log_id" in again.json()

    failed = client.post(
        url,
        {"operation": "course.sync", "status": "failed", "section_id": section.pk, "message": "Course archived"},
        format="json",
    )
    assert failed.status_code == 201
    link = LmsCourseLink.objects.get(section=section)
    assert link.status == LinkStatus.FAILED and link.last_error == "Course archived"
    client.post(
        url,
        {
            "operation": "course.sync",
            "status": "succeeded",
            "section_id": section.pk,
            "external_course_id": "moodle-42",
            "external_url": "https://lms.test/course/view.php?id=42",
        },
        format="json",
    )
    link.refresh_from_db()
    assert link.status == LinkStatus.LINKED and link.external_course_id == "moodle-42" and link.last_error is None
    assert client.post(url, {"operation": "nope", "status": "succeeded"}, format="json").status_code == 400
    other = SectionFactory(published=True)
    assert (
        client.post(
            url, {"operation": "course.sync", "status": "succeeded", "section_id": other.pk}, format="json"
        ).status_code
        == 400
    )


def test_delivered_scores_become_the_grade_entry_draft(linked: dict[str, Any]) -> None:
    client: APIClient = linked["client"]
    enrollment = linked["enrollment"]
    external = LmsUserLink.objects.get(user=linked["student"]).external_user_id
    url = "/api/v1/lms/platforms/TEST/scores/"
    course = f"course-{linked['section'].pk}"
    assert client.post(url, {"external_course_id": course, "scores": {external: 101}}, format="json").status_code == 400
    unknown = client.post(url, {"external_course_id": "nope", "scores": {external: 80}}, format="json")
    assert unknown.status_code == 400 and "external_course_id" in unknown.json()

    response = client.post(url, {"external_course_id": course, "scores": {external: 91.5, "user-x": 50}}, format="json")
    assert response.status_code == 201
    assert response.json() == {"section_id": linked["section"].pk, "scores": 2, "matched": 1}
    log = LmsSyncLog.objects.get(operation=SyncOperation.GRADES_DELIVERED)
    assert log.status == SyncStatus.SUCCEEDED and log.payload["scores"][external] == 91.5

    # The null connector reports no scores, so the latest delivery is the draft; nothing is saved.
    assert PullGrades().handle(linked["platform"], linked["section"]) == {enrollment.pk: 91.5}
    enrollment.refresh_from_db()
    assert enrollment.score is None
    # Without lms.manage nobody delivers.
    teacher = token_client(issue(linked["teacher"]))
    assert teacher.post(url, {"external_course_id": course, "scores": {external: 80}}, format="json").status_code == 403
