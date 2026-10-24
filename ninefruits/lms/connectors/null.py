"""The ``null`` driver (original ``NullConnector``): talks to nobody."""

from __future__ import annotations

from typing import TYPE_CHECKING

from .base import PlatformCourse

if TYPE_CHECKING:
    from ninefruits.lms.models import LmsPlatform
    from ninefruits.offering.models import Section
    from ninefruits.security.models import User

DEFAULT_BASE_URL = "https://lms.example.test"


class NullConnector:
    """Returns deterministic identifiers (``course-{section id}``, ``user-{user id}``) so links,
    logs, events and the reconcile loop can be exercised before a real platform is connected.
    It reports nobody on the platform and no scores, so reconciling adds every member back."""

    def ensure_course(self, platform: LmsPlatform, section: Section) -> PlatformCourse:
        base = (platform.base_url or DEFAULT_BASE_URL).rstrip("/")
        return {"id": f"course-{section.pk}", "url": f"{base}/course/view.php?id={section.pk}"}

    def ensure_user(self, platform: LmsPlatform, user: User) -> str:
        return f"user-{user.pk}"

    def enroll(self, platform: LmsPlatform, course_id: str, user_id: str, role: str) -> None:
        """Nothing to call."""

    def unenroll(self, platform: LmsPlatform, course_id: str, user_id: str) -> None:
        """Nothing to call."""

    def members(self, platform: LmsPlatform, course_id: str) -> dict[str, str]:
        return {}

    def final_scores(self, platform: LmsPlatform, course_id: str) -> dict[str, float]:
        return {}
