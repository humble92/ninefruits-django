"""The legacy YUST rules as settings (original ``YustLegacyProfileSeeder``)."""

from __future__ import annotations

from decimal import Decimal

from ninefruits.setup.seeders.profiles import SetupProfile
from ninefruits.setup.seeders.profiles.korean_university import KoreanUniversityProfileSeeder, scale_43, seed_scale


class YustLegacyProfileSeeder(SetupProfile):
    """Grading (legacy SSCOREDEF and the GPA views, original ADR 0011): the 4.3 scale with
    minus grades (A+ 4.3, confirmed 2026-10-22), P/N and I is the institution's scale; score
    ranges are in steps of three points (the legacy entered letters only). Includes the Korean
    university profile.

    The original profile also sets credit limit policies by admission year and nursing
    (Phase 5), keeps credit bank courses (codes 009*, 900*) outside the limit (Phase 4) and
    sets the grading policy (Phase 6); those phases add their steps to ``LATER_PHASE_STEPS``.
    Idempotent."""

    key = "yust-legacy"
    label = "YUST legacy rules"
    description = (
        "Credit limits by admission year and nursing, credit bank courses outside the limit, the 4.3 grade scale "
        "and grading policy (includes korean-university)"
    )

    #: Org units whose students get the nursing credit limits (Phase 5).
    NURSING_UNIT_CODES: tuple[str, ...] = ("NURS",)

    #: Dotted paths of functions ``(seeder) -> None`` added by later phases.
    LATER_PHASE_STEPS: list[str] = []

    def run(self) -> None:
        # Before the Korean data, so the 4.3 scale is the one fixed as the institution's.
        self.grade_scale()
        self.call(KoreanUniversityProfileSeeder)

        from django.utils.module_loading import import_string

        for path in self.LATER_PHASE_STEPS:
            import_string(path)(self)

    def grade_scale(self) -> None:
        """The 4.3 scale is the institution's scale unless one was fixed already (e.g. by
        ``setup_install --grade-scale``)."""
        seed_scale(
            "YUST43",
            {
                "en": "4.3 scale (YUST)",
                "ko": "4.3 만점(YUST)",
                "zh-hans": "4.3 分制（YUST）",
                "lo": "ລະບົບ 4.3 ຄະແນນ (YUST)",
            },
            Decimal("4.3"),
            True,
            scale_43({"P": (True,), "N": (False,), "I": (False, "both")}),
        )
