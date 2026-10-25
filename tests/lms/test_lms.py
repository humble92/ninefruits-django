"""LMS integration (original ``tests/Feature/Lms/LmsTest.php``): domain events queue section and
roster synchronization for active platforms only; the course, its members and the user are
linked and every step is logged; ``lms_sync`` (dry run, unknown platform, a driver without a
connector) and the reconcile; platform scores loaded into the grade entry screen as a draft; the
course link in the portal; the admin screens; encrypted credentials; row level security."""

from __future__ import annotations

import io
from typing import Any

import pytest
from django.core import serializers
from django.core.management import call_command
from django.db import connection

from ninefruits.audit.models import ActivityLog
from ninefruits.core.db import session_context
from ninefruits.lms import tasks
from ninefruits.lms.actions import PullGrades, ReconcilePlatform
from ninefruits.lms.connectors import NullConnector, connectors
from ninefruits.lms.enums import LinkStatus, SyncOperation, SyncStatus
from ninefruits.lms.models import LmsCourseLink, LmsPlatform, LmsSyncLog, LmsUserLink
from ninefruits.offering.actions import ChangeSectionStatus
from ninefruits.offering.enums import SectionStatus
from ninefruits.registration.actions import DropEnrollment
from ninefruits.term.enums import TermWindowType
from tests.factories.registration import EnrollmentFactory
from tests.factories.term import TermWindowFactory

from .conftest import Lms, signed_in

pytestmark = pytest.mark.django_db


def run(name: str, *args: str) -> tuple[int, str]:
    out = io.StringIO()
    code = call_command(name, *args, stdout=out, stderr=out)
    return code, out.getvalue()


def publish(lms: Lms, capture: Any) -> None:
    """Publishing dispatches ``SectionPublished``; the queued task runs after the commit."""
    with capture(execute=True):
        ChangeSectionStatus()(lms.section, SectionStatus.PUBLISHED, lms.admin)
    lms.section.refresh_from_db()


def enroll(lms: Lms) -> Any:
    return EnrollmentFactory(section=lms.section, student_record=lms.record)


class Recorder:
    def __init__(self) -> None:
        self.calls: list[tuple[Any, ...]] = []

    def __call__(self, *args: Any, **kwargs: Any) -> None:
        self.calls.append((*args, kwargs))


def test_queues_section_and_roster_synchronization_from_the_domain_events(
    lms: Lms, monkeypatch: pytest.MonkeyPatch, django_capture_on_commit_callbacks: Any
) -> None:
    sections, enrollments = Recorder(), Recorder()
    monkeypatch.setattr(tasks.sync_section, "delay", sections)
    monkeypatch.setattr(tasks.sync_enrollment, "delay", enrollments)

    publish(lms, django_capture_on_commit_callbacks)
    assert sections.calls == [(lms.platform.pk, lms.section.pk, {})]

    enrollment = enroll(lms)
    with django_capture_on_commit_callbacks(execute=True):
        DropEnrollment().drop(enrollment, lms.admin, "Staff drop")
    assert enrollments.calls == [(lms.platform.pk, enrollment.pk, {"removed": True})]

    # An inactive platform gets nothing.
    lms.platform.is_active = False
    lms.platform.save()
    with django_capture_on_commit_callbacks(execute=True):
        ChangeSectionStatus()(lms.section, SectionStatus.DRAFT, lms.admin)
        ChangeSectionStatus()(lms.section, SectionStatus.PUBLISHED, lms.admin)
    assert len(sections.calls) == 1


def test_links_the_course_its_members_and_the_user_logs_every_step_and_reconciles(
    lms: Lms, django_capture_on_commit_callbacks: Any
) -> None:
    publish(lms, django_capture_on_commit_callbacks)
    enroll(lms)

    assert run("lms_sync", "NOPE")[0] == 1
    code, output = run("lms_sync", "TEST", "--dry-run")
    assert code == 0 and "Dry run: 1 section(s), 0 member(s), 0 failed." in output
    assert LmsSyncLog.objects.filter(status=SyncStatus.SKIPPED).count() == 1

    code, output = run("lms_sync", "TEST", f"--term={lms.term.code}", f"--actor={lms.admin.email}")
    assert code == 0 and "1 section(s), 2 member(s), 0 failed." in output
    link = LmsCourseLink.objects.get(section=lms.section)
    assert link.status == LinkStatus.LINKED
    assert link.external_course_id == f"course-{lms.section.pk}"
    assert "https://lms.test/" in link.external_url
    assert LmsUserLink.objects.get(user=lms.student).external_user_id == f"user-{lms.student.pk}"
    # Publishing already synchronized the course and the instructor through the event.
    succeeded = LmsSyncLog.objects.filter(status=SyncStatus.SUCCEEDED)
    assert succeeded.filter(operation=SyncOperation.ENROLLMENT_ADD).count() == 3
    assert succeeded.filter(operation=SyncOperation.COURSE_SYNC).count() == 2

    # The null connector reports nobody on the platform: reconcile adds everyone back and logs the difference.
    summary = ReconcilePlatform().handle(lms.platform, lms.term)
    assert summary == {"sections": 1, "added": 2, "removed": 0, "failed": 0}
    assert len(LmsSyncLog.objects.get(operation=SyncOperation.RECONCILE).payload["missing"]) == 2
    assert run("lms_reconcile", "TEST", "--dry-run")[0] == 0
    assert run("lms_reconcile", "NOPE")[0] == 1

    # A driver without a connector fails the sync and marks the link.
    lms.platform.driver = "moodle"
    lms.platform.save()
    assert run("lms_sync", "TEST", f"--term={lms.term.code}")[0] == 2
    link.refresh_from_db()
    assert link.status == LinkStatus.FAILED
    assert "moodle" in link.last_error


class ScoringConnector(NullConnector):
    """A platform reporting 87.5 for every user it knows."""

    def final_scores(self, platform: LmsPlatform, course_id: str) -> dict[str, float]:
        return dict.fromkeys(LmsUserLink.objects.values_list("external_user_id", flat=True), 87.5)


def test_loads_platform_scores_into_the_grade_entry_screen_as_a_draft(
    lms: Lms, django_capture_on_commit_callbacks: Any
) -> None:
    # Importing scores is grade entry: the instructor needs an open grade entry window (security review H5).
    from django.utils import timezone

    now = timezone.now().replace(microsecond=0)
    TermWindowFactory(
        term=lms.term,
        window_type=TermWindowType.GRADE_ENTRY,
        session=lms.section.session,
        opens_at=now - timezone.timedelta(days=1),
        closes_at=now + timezone.timedelta(weeks=1),
    )
    publish(lms, django_capture_on_commit_callbacks)
    enrollment = enroll(lms)
    run("lms_sync", "TEST", f"--term={lms.term.code}")
    lms.section.evaluation_method = "absolute"
    lms.section.save()

    with connectors().override("null", ScoringConnector()):
        assert PullGrades().handle(lms.platform, lms.section) == {enrollment.pk: 87.5}
        client = signed_in(lms.teacher)
        url = f"/portal/sections/{lms.section.pk}/grades/"
        page = client.get(url)
        assert page.status_code == 200
        assert "Load scores from the LMS" in page.content.decode()
        response = client.post(url, {"action": "import_lms"})
    html = response.content.decode()
    assert response.status_code == 200
    assert f'name="grade-{enrollment.pk}-score" value="87.5"' in html
    assert "1 score(s) loaded from the LMS as a draft. Check them and save." in html
    enrollment.refresh_from_db()
    assert enrollment.score is None
    assert LmsSyncLog.objects.filter(operation=SyncOperation.GRADES_PULL, status=SyncStatus.SUCCEEDED).count() == 2

    # Someone who may not enter the grades cannot import them.
    assert signed_in(lms.student).post(url, {"action": "import_lms"}).status_code == 403


def test_refuses_to_load_platform_scores_for_someone_who_may_not_enter_the_grades(lms: Lms) -> None:
    # Security review H5: importing scores is grade entry. Without an open grade entry window the
    # instructor may not, nor may an unrelated account; staff with grades.manage in scope may.
    from django.core.exceptions import PermissionDenied

    from ninefruits.security.enums import Permission
    from tests.factories.security import UserFactory

    for actor in (lms.teacher, lms.student):
        with pytest.raises(PermissionDenied):
            PullGrades().handle(lms.platform, lms.section, actor)
    registrar = UserFactory(permissions=[Permission.GRADES_MANAGE])
    assert PullGrades().handle(lms.platform, lms.section, registrar) == {}
    assert not LmsSyncLog.objects.filter(operation=SyncOperation.GRADES_PULL).exists()


def test_shows_the_course_link_in_the_portal_and_restricts_links_and_logs_by_permission_and_rls(
    lms: Lms, django_capture_on_commit_callbacks: Any
) -> None:
    publish(lms, django_capture_on_commit_callbacks)
    enroll(lms)
    run("lms_sync", "TEST", f"--term={lms.term.code}")

    page = signed_in(lms.student).get(f"/portal/sections/{lms.section.pk}/")
    assert page.status_code == 200 and "https://lms.test/" in page.content.decode()
    assert "Open the course on Test LMS" in page.content.decode()
    page = signed_in(lms.teacher).get("/portal/teaching/")
    assert page.status_code == 200 and "https://lms.test/" in page.content.decode()

    admin = signed_in(lms.admin)
    link = LmsCourseLink.objects.get(section=lms.section)
    for url in (
        "/admin/lms/lmsplatform/",
        f"/admin/lms/lmsplatform/{lms.platform.pk}/change/",
        "/admin/lms/lmsplatform/add/",
        "/admin/lms/lmscourselink/",
        f"/admin/lms/lmscourselink/?platform={lms.platform.pk}&status=linked&term={lms.term.pk}&q=",
        f"/admin/lms/lmscourselink/{link.pk}/resync/",
        "/admin/lms/lmssynclog/",
        "/admin/lms/lmssynclog/?operation=course.sync&status=succeeded",
        f"/admin/lms/lmssynclog/{LmsSyncLog.objects.first().pk}/change/",
    ):
        assert admin.get(url).status_code == 200, url

    response = admin.post(
        "/admin/lms/lmsplatform/add/",
        {
            "code": "MOODLE",
            "driver": "moodle",
            "name__en": "Moodle",
            "name__ko": "무들",
            "name__zh-hans": "Moodle",
            "base_url": "https://moodle.test",
            "credentials_text": "token=s3cr3t-value",
            "should_sync_enrollments": "on",
        },
    )
    assert response.status_code == 302, response.content.decode()[:2000]
    moodle = LmsPlatform.objects.get(code="MOODLE")
    assert moodle.credentials == {"token": "s3cr3t-value"}
    assert moodle.is_active is False
    with connection.cursor() as cursor:
        cursor.execute("SELECT credentials FROM lms_platforms WHERE code = %s", ["MOODLE"])
        stored = cursor.fetchone()[0]
    assert "s3cr3t" not in stored
    assert "s3cr3t" not in serializers.serialize("json", [moodle])
    assert "s3cr3t" not in admin.get(f"/admin/lms/lmsplatform/{moodle.pk}/change/").content.decode()

    context = session_context()
    context.for_user(lms.student.pk)
    try:
        assert LmsCourseLink.objects.count() == 1
        assert LmsUserLink.objects.count() == 1
        assert LmsSyncLog.objects.count() == 0
        context.for_user(lms.admin.pk)
        assert LmsSyncLog.objects.count() > 0
    finally:
        context.reset()


def test_editing_a_platform_keeps_credentials_unless_new_ones_are_given(lms: Lms) -> None:
    lms.platform.credentials = {"token": "first"}
    lms.platform.save()
    admin = signed_in(lms.admin)
    url = f"/admin/lms/lmsplatform/{lms.platform.pk}/change/"
    data = {
        "code": "TEST",
        "driver": "null",
        "name__en": "Test LMS",
        "base_url": "https://lms.test",
        "credentials_text": "",
        "is_active": "on",
        "should_sync_enrollments": "on",
        "should_pull_grades": "on",
    }
    assert admin.post(url, data).status_code == 302
    lms.platform.refresh_from_db()
    assert lms.platform.credentials == {"token": "first"}

    assert admin.post(url, {**data, "credentials_text": "token=second\nsecret = s3"}).status_code == 302
    lms.platform.refresh_from_db()
    assert lms.platform.credentials == {"token": "second", "secret": "s3"}
    assert lms.platform.credential("secret") == "s3"

    response = admin.post(url, {**data, "credentials_text": "no equals sign"})
    assert response.status_code == 200 and "write key=value" in response.content.decode()

    # The data audit never holds the values (secret column of the trigger).
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT coalesce(string_agg(old_values::text || ' ' || new_values::text, ' '), '') "
            "FROM audit.record_changes WHERE table_name = %s",
            ["lms_platforms"],
        )
        changes = cursor.fetchone()[0]
    assert "first" not in changes and "second" not in changes and "s3" not in changes


def test_resync_row_action_reports_success_and_connector_failures(
    lms: Lms, django_capture_on_commit_callbacks: Any
) -> None:
    publish(lms, django_capture_on_commit_callbacks)
    link = LmsCourseLink.objects.get(section=lms.section)
    admin = signed_in(lms.admin)
    response = admin.post(f"/admin/lms/lmscourselink/{link.pk}/resync/", follow=True)
    assert "Synchronized: 1 member(s)." in response.content.decode()

    lms.platform.driver = "openedx"
    lms.platform.save()
    response = admin.post(f"/admin/lms/lmscourselink/{link.pk}/resync/", follow=True)
    assert "No connector for LMS driver [openedx]." in response.content.decode()
    link.refresh_from_db()
    assert link.status == LinkStatus.FAILED

    # Without lms.manage the screens are closed.
    assert signed_in(lms.teacher).get("/admin/lms/lmscourselink/").status_code in (302, 403)


def test_enrollment_events_add_and_remove_members_through_the_tasks(
    lms: Lms, django_capture_on_commit_callbacks: Any
) -> None:
    publish(lms, django_capture_on_commit_callbacks)
    enrollment = enroll(lms)
    tasks.sync_enrollment.delay(lms.platform.pk, enrollment.pk)
    add = LmsSyncLog.objects.filter(operation=SyncOperation.ENROLLMENT_ADD, enrollment=enrollment).get()
    assert add.status == SyncStatus.SUCCEEDED and add.payload["role"] == "student"

    with django_capture_on_commit_callbacks(execute=True):
        DropEnrollment().drop(enrollment, lms.admin, "Staff drop")
    removed = LmsSyncLog.objects.get(operation=SyncOperation.ENROLLMENT_REMOVE, enrollment=enrollment)
    assert removed.status == SyncStatus.SUCCEEDED
    assert removed.payload == {"external_user_id": f"user-{lms.student.pk}"}

    # Inactive platforms are skipped by the tasks; the nightly task reconciles active ones.
    assert tasks.sync_section.delay(lms.platform.pk + 1000, lms.section.pk).get() is None
    assert tasks.reconcile.delay().get() == 0
    # The scheduled run is audited like the command (the original scheduler ran lms:reconcile).
    entry = ActivityLog.objects.filter(log_name="command", properties__command="lms_reconcile").latest("id")
    assert entry.properties["result"] == {"TEST": {"sections": 1, "added": 1, "removed": 0, "failed": 0}}


def test_visible_to_matches_row_level_security(lms: Lms, django_capture_on_commit_callbacks: Any) -> None:
    publish(lms, django_capture_on_commit_callbacks)
    enroll(lms)
    run("lms_sync", "TEST")
    context = session_context()
    for user in (lms.student, lms.teacher, lms.admin):
        context.for_user(user.pk)
        try:
            for model in (LmsCourseLink, LmsUserLink, LmsSyncLog):
                in_database = set(model.objects.values_list("pk", flat=True))
                in_application = set(model.objects.visible_to(user).values_list("pk", flat=True))
                assert in_database == in_application, (model.__name__, user.email)
        finally:
            context.reset()


def test_sync_log_payload_is_json_and_shown_on_the_detail_page(
    lms: Lms, django_capture_on_commit_callbacks: Any
) -> None:
    publish(lms, django_capture_on_commit_callbacks)
    log = LmsSyncLog.objects.get(operation=SyncOperation.COURSE_SYNC)
    assert log.payload == {
        "id": f"course-{lms.section.pk}",
        "url": f"https://lms.test/course/view.php?id={lms.section.pk}",
    }
    page = signed_in(lms.admin).get(f"/admin/lms/lmssynclog/{log.pk}/change/").content.decode()
    assert "&quot;id&quot;: &quot;course-" in page
