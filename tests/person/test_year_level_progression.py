from datetime import date, timedelta

import pytest
from django.core.management import call_command
from django.test import Client
from django.urls import reverse
from django.utils import timezone

from ninefruits.grading.models import TermRecord
from ninefruits.person.actions.year_levels import ManageYearLevels
from ninefruits.person.enums import StudentStatus
from ninefruits.person.models import YearLevelRule, YearLevelRun
from ninefruits.security.enums import MfaEnforcement, Permission
from ninefruits.settings.groups.security import SecuritySettings
from tests.factories.organization import ProgramFactory
from tests.factories.person import StudentRecordFactory
from tests.factories.security import UserFactory
from tests.factories.term import TermFactory

pytestmark = [pytest.mark.django_db, pytest.mark.usefixtures("essential_data")]


def test_applies_only_the_reviewed_and_current_student_records() -> None:
    staff = UserFactory(permissions=[Permission.STUDENT_RECORDS_MANAGE, Permission.INSTITUTION_SETTINGS_MANAGE])
    service = ManageYearLevels()
    service.save_rule(
        YearLevelRule(),
        {
            "name": {"en": "Credits"},
            "basis": "credits",
            "is_default": True,
            "thresholds": [{"minimum": 24}, {"minimum": 48}],
        },
        staff,
    )
    override = service.save_rule(
        YearLevelRule(),
        {
            "name": {"en": "Terms"},
            "basis": "terms",
            "is_default": False,
            "thresholds": [{"minimum": 1}],
        },
        staff,
    )
    target = TermFactory(start_date=date(2026, 9, 1), end_date=date(2026, 12, 31))
    previous = TermFactory(start_date=date(2026, 3, 2), end_date=date(2026, 6, 30))
    retake_term = TermFactory(start_date=date(2026, 7, 1), end_date=date(2026, 8, 12))
    program = ProgramFactory(year_level_rule=override)
    admission = date(2025, 3, 1)
    eligible, excluded, stale, unclosed, retake = StudentRecordFactory.create_batch(5, admission_date=admission)
    overriding = StudentRecordFactory(program=program, admission_date=admission)
    closed_at = timezone.now()
    for student, credits in [
        (eligible, 50),
        (excluded, 24),
        (stale, 24),
        (overriding, 1),
        (unclosed, 100),
        (retake, 15),
    ]:
        TermRecord.objects.create(
            student_record=student,
            term=previous,
            earned_credits=credits,
            attempted_credits=credits,
            cumulative_earned_credits=credits,
            calculated_at=closed_at,
            closed_at=None if student == unclosed else closed_at,
        )

    TermRecord.objects.create(
        student_record=retake,
        term=retake_term,
        earned_credits=15,
        attempted_credits=15,
        cumulative_earned_credits=15,
        calculated_at=closed_at,
        closed_at=closed_at,
    )

    run = service.preview(target.pk, retake_term.end_date, staff)
    assert run.changes.count() == 4
    service.exclude(run.pk, run.changes.get(student_record=excluded).pk, staff)
    service.schedule(run.pk, timezone.now() + timedelta(minutes=5), staff)
    assert service.apply_due() == 0
    stale.status = StudentStatus.ON_LEAVE
    stale.save(update_fields=["status"])
    YearLevelRun.objects.filter(pk=run.pk).update(scheduled_at=timezone.now() - timedelta(seconds=1))
    assert call_command("students_apply_year_levels") == 0
    assert service.apply_due() == 0
    for student, level in [(eligible, 3), (overriding, 2), (excluded, 1), (stale, 1), (unclosed, 1), (retake, 1)]:
        student.refresh_from_db()
        assert student.year_level == level
    assert run.changes.get(student_record=stale).outcome == "stale"


def test_staff_can_save_a_rule_and_open_the_preview(client: Client) -> None:
    settings = SecuritySettings.load()
    settings.mfa_enforcement = MfaEnforcement.DISABLED
    settings.save()
    staff = UserFactory(
        permissions=[
            Permission.ADMIN_PANEL_ACCESS,
            Permission.STUDENT_RECORDS_MANAGE,
            Permission.INSTITUTION_SETTINGS_MANAGE,
        ]
    )
    client.force_login(staff)
    rules_url = reverse("admin:year_level_rules")
    preview_url = reverse("admin:year_level_progression")
    assert client.get(rules_url).status_code == 200
    assert (
        client.post(
            rules_url,
            {
                "name__en": "Standard",
                "basis": "credits",
                "minimums": "24, 48, 72",
                "is_default": "on",
            },
        ).status_code
        == 302
    )
    assert YearLevelRule.objects.get(is_default=True).thresholds[-1] == {"minimum": "72"}
    assert client.get(preview_url).status_code == 200
    term = TermFactory(start_date=date(2026, 9, 1), end_date=date(2026, 12, 31))
    response = client.post(preview_url, {"action": "preview", "term": term.pk, "cutoff_date": "2026-06-30"})
    assert response.status_code == 302
    assert client.get(response["Location"]).status_code == 200
