"""Installation (``setup_install``) and demo data (``setup_demo``) configuration (original
``config/setup.php``, porting-plan 13.4)."""

from __future__ import annotations

#: Profile seeders offered by ``setup_install`` (dotted paths of ``SetupProfile`` classes).
PROFILES: tuple[str, ...] = (
    "ninefruits.setup.seeders.profiles.korean_university.KoreanUniversityProfileSeeder",
    "ninefruits.setup.seeders.profiles.yust_legacy.YustLegacyProfileSeeder",
)

#: Students per demo size. Other volumes scale from this.
DEMO_SIZES: dict[str, int] = {
    # For tests and quick checks: every kind of demo data, as few rows as possible.
    "tiny": 20,
    "small": 100,
    "medium": 2000,
    "large": 20000,
}

#: Demo accounts use this reserved domain only (RFC 2606 ``.test``).
DEMO_EMAIL_DOMAIN = "demo.test"

#: Password of the fixed demo accounts printed by ``setup_demo``.
DEMO_PASSWORD = "demo-password"  # noqa: S105 - fictional demo accounts, never in production
