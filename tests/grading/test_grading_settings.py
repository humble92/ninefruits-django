"""The grading settings group (original ``database/settings/2026_10_22_006010_create_grading_settings``
and ``2026_10_23_000110_add_relative_grade_caps``), the legacy YUST profile's grading policy and
the "Grading policy" page."""

from __future__ import annotations

from typing import Any

import pytest
from django.test import Client

from ninefruits.audit.models import ActivityLog
from ninefruits.core.db import session_context
from ninefruits.grading.settings import GradingSettings
from ninefruits.grading.settings_pages import format_caps, parse_caps
from ninefruits.security.enums import Permission
from tests.factories.security import UserFactory

pytestmark = pytest.mark.django_db


def test_the_data_migrations_give_the_original_defaults() -> None:
    settings = GradingSettings.load()
    assert settings.model_dump() == {
        "gpa_decimals": 2,
        "gpa_rounding": "round",
        "retake_policy": "latest",
        "retake_max_grade": None,
        "relative_grade_caps": {"A": 30, "B": 40},
        "relative_cap_tolerance_percent": 1,
        "relative_minimum_students": 10,
        "standing_regular_terms_only": True,
        "warning_gpa_below": 1.75,
        "dismissal_warning_count": 0,
        "dismissal_consecutive_only": False,
        "honors_min_gpa": 4.0,
        "honors_min_credits": 15,
        "honors_exclude_failing": True,
    }


def test_the_legacy_profile_sets_the_legacy_grading_policy_idempotently(essential_data: None) -> None:
    from ninefruits.setup.seeders.profiles.yust_legacy import YustLegacyProfileSeeder

    YustLegacyProfileSeeder()()
    YustLegacyProfileSeeder()()
    GradingSettings.invalidate()
    settings = GradingSettings.load()
    assert (settings.gpa_decimals, settings.warning_gpa_below, settings.dismissal_warning_count) == (3, 1.3, 4)
    assert (settings.honors_min_gpa, settings.honors_exclude_failing) == (0.0, False)


def test_parses_and_formats_the_grade_caps() -> None:
    assert parse_caps("a=30, B:40\nC = 50") == {"A": 30, "B": 40, "C": 50}
    assert parse_caps("") == {}
    assert format_caps({"B": 40, "A": 30}) == "A=30, B=40"
    with pytest.raises(Exception, match="letter and a percentage"):
        parse_caps("AB=30")


def test_the_policy_page_saves_the_settings_with_an_audit_entry(korean_scale: Any) -> None:
    manager = UserFactory(permissions=[Permission.ADMIN_PANEL_ACCESS, Permission.GRADING_POLICIES_MANAGE])
    client = Client()
    client.force_login(manager)
    session_context().reset()

    page = client.get("/admin/settings/grading/")
    assert page.status_code == 200
    assert "4.5 scale" in page.content.decode()
    data = {
        "gpa_decimals": "3",
        "gpa_rounding": "floor",
        "retake_policy": "best",
        "retake_max_grade": "A0",
        "relative_grade_caps": "A=25, B=35",
        "relative_cap_tolerance_percent": "2",
        "relative_minimum_students": "12",
        "warning_gpa_below": "1.5",
        "standing_regular_terms_only": "on",
        "dismissal_warning_count": "3",
        "honors_min_gpa": "3.8",
        "honors_min_credits": "12",
        "honors_exclude_failing": "on",
    }
    response = client.post("/admin/settings/grading/", data)
    assert response.status_code == 302
    settings = GradingSettings.load()
    assert settings.gpa_rounding == "floor"
    assert settings.retake_max_grade == "A0"
    assert settings.relative_grade_caps == {"A": 25, "B": 35}
    assert settings.warning_gpa_below == 1.5
    assert settings.dismissal_consecutive_only is False
    entry = ActivityLog.objects.filter(event="settings.updated").latest("id")
    assert entry.properties["group"] == "grading"

    assert Client().get("/admin/settings/grading/").status_code in (302, 403)
    other = UserFactory(permissions=[Permission.ADMIN_PANEL_ACCESS, Permission.GRADES_VIEW])
    client.force_login(other)
    assert client.get("/admin/settings/grading/").status_code == 403
