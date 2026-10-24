"""What a platform connector does (original ``App\\Domain\\Lms\\Contracts\\LmsConnector``,
porting-plan 12, ADR 0017).

The academic system owns users, sections, rosters and final grades; the LMS owns content and raw
scores. A connector talks to one kind of platform. It gets the platform (base URL, credentials,
options) with every call and must not keep state, so one connector serves several platforms of
the same driver (one Moodle per campus). Errors are raised: the sync log records the failure and
the Celery task retries. Writing a connector: ``docs/lms-integration-guide.md``."""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, TypedDict, runtime_checkable

if TYPE_CHECKING:
    from ninefruits.lms.models import LmsPlatform
    from ninefruits.offering.models import Section
    from ninefruits.security.models import User


class PlatformCourse(TypedDict):
    """The course on the platform: its id and the URL people open (``None`` without one)."""

    id: str
    url: str | None


@runtime_checkable
class LmsConnector(Protocol):
    def ensure_course(self, platform: LmsPlatform, section: Section) -> PlatformCourse:
        """Creates or finds the course for the section; the same section gives the same id."""
        ...

    def ensure_user(self, platform: LmsPlatform, user: User) -> str:
        """Creates or finds the user; returns their id on the platform."""
        ...

    def enroll(self, platform: LmsPlatform, course_id: str, user_id: str, role: str) -> None:
        """Adds the user to the course with the role (``instructor`` or ``student``)."""
        ...

    def unenroll(self, platform: LmsPlatform, course_id: str, user_id: str) -> None: ...

    def members(self, platform: LmsPlatform, course_id: str) -> dict[str, str]:
        """The users enrolled in the course on the platform: external user id -> role."""
        ...

    def final_scores(self, platform: LmsPlatform, course_id: str) -> dict[str, float]:
        """Final course scores: external user id -> score (0-100 as the platform reports it)."""
        ...
