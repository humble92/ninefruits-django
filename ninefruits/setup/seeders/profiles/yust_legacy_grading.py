"""Phase 6 step of the ``yust-legacy`` profile (original ``YustLegacyProfileSeeder::gradingPolicy``,
ADR 0011): GPA rounded to 3 decimals; the latest attempt of a retake counts; a warning below a
term GPA of 1.3 in regular terms; dismissal review after 4 warnings in all. The legacy honors list
was a plain top N, so every student with a GPA is ranked."""

from __future__ import annotations

from typing import Any

LEGACY_POLICY: dict[str, Any] = {
    "gpa_decimals": 3,
    "gpa_rounding": "round",
    "retake_policy": "latest",
    "retake_max_grade": None,
    "standing_regular_terms_only": True,
    "warning_gpa_below": 1.3,
    "dismissal_warning_count": 4,
    "dismissal_consecutive_only": False,
    "honors_min_gpa": 0.0,
    "honors_min_credits": 0.0,
    "honors_exclude_failing": False,
}


def seed_grading_policy(profile: Any) -> None:
    from ninefruits.grading.settings import GradingSettings

    settings = GradingSettings.load()
    for name, value in LEGACY_POLICY.items():
        setattr(settings, name, value)
    settings.save()
