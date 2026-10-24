"""Pushes a section to a platform (original ``SyncSection``): the course, its instructors and its
enrolled students. Idempotent: links are created or kept and every member is ensured again."""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any, TypedDict

from django.core.exceptions import PermissionDenied
from django.utils import timezone

from ninefruits.core.db import session_context
from ninefruits.lms.connectors import ConnectorRegistry, connectors
from ninefruits.lms.enums import INSTRUCTOR, STUDENT, LinkStatus, SyncOperation
from ninefruits.lms.models import LmsCourseLink, LmsPlatform, LmsUserLink
from ninefruits.lms.services.sync_logger import MESSAGE_MAX, StepResult, SyncLogger
from ninefruits.security.enums import Permission


class SectionSummary(TypedDict):
    course: str
    members: int


def account_of(person: Any) -> Any:
    """The person's user account, or ``None`` (only people with an account are synchronized)."""
    return getattr(person, "user", None) if person is not None else None


def enrolled(section_id: int) -> Any:
    """The section's enrolled students with their accounts."""
    from ninefruits.registration.enums import EnrollmentStatus
    from ninefruits.registration.models import Enrollment

    return (
        Enrollment.objects.filter(section_id=section_id, status=EnrollmentStatus.ENROLLED)
        .select_related("student_record__person__user")
        .order_by("pk")
    )


def instructor_accounts(section: Any) -> list[Any]:
    from ninefruits.offering.models import SectionInstructor

    assignments = (
        SectionInstructor.objects.filter(section_id=section.pk)
        .select_related("instructor__person__user")
        .order_by("pk")
    )
    users = (account_of(assignment.instructor.person) for assignment in assignments)
    return [user for user in users if user is not None]


@contextmanager
def as_platform_system(actor: Any, name: str) -> Iterator[None]:
    """Platform data (links, logs, rosters) is written in the system context. A signed-in actor
    (an admin screen) must hold ``lms.manage``; tasks and commands already run as the system."""
    if actor is not None:
        if not actor.has_perm(Permission.LMS_MANAGE):
            raise PermissionDenied
        with session_context().system(name):
            yield
        return
    yield


class SyncSection:
    def __init__(self, registry: ConnectorRegistry | None = None, log: SyncLogger | None = None) -> None:
        self.registry = registry or connectors()
        self.log = log or SyncLogger()

    def __call__(self, platform: LmsPlatform, section: Any, dry_run: bool = False, actor: Any = None) -> SectionSummary:
        return self.handle(platform, section, dry_run, actor)

    def handle(self, platform: LmsPlatform, section: Any, dry_run: bool = False, actor: Any = None) -> SectionSummary:
        with as_platform_system(actor, "lms.sync"):
            return self._handle(platform, section, dry_run)

    def _handle(self, platform: LmsPlatform, section: Any, dry_run: bool) -> SectionSummary:
        link, _created = LmsCourseLink.objects.get_or_create(platform=platform, section=section)
        summary: SectionSummary = {"course": "", "members": 0}

        try:
            # Resolved here: a driver without a connector marks the link failed like any other error.
            connector = self.registry.for_platform(platform)

            def course() -> StepResult:
                found = connector.ensure_course(platform, section)
                link.external_course_id = found["id"]
                link.external_url = found.get("url")
                link.status = LinkStatus.LINKED
                link.last_synced_at = timezone.now()
                link.last_error = None
                link.save()
                summary["course"] = found["id"]
                return dict(found)

            self.log.run(platform, SyncOperation.COURSE_SYNC, {"section_id": section.pk}, course, dry_run)
        except Exception as error:
            link.status = LinkStatus.FAILED
            link.last_error = str(error)[:MESSAGE_MAX]
            link.save(update_fields=["status", "last_error", "updated_at"])
            raise

        if dry_run or not platform.should_sync_enrollments:
            return summary

        for user in instructor_accounts(section):
            self.member(platform, link, user, INSTRUCTOR)
            summary["members"] += 1
        for enrollment in enrolled(section.pk):
            user = account_of(enrollment.student_record.person)
            if user is not None:
                self.member(platform, link, user, STUDENT, enrollment)
                summary["members"] += 1
        return summary

    def member(self, platform: LmsPlatform, link: LmsCourseLink, user: Any, role: str, enrollment: Any = None) -> None:
        """Ensures the user on the platform (user link) and adds them to the course."""
        connector = self.registry.for_platform(platform)

        def add() -> StepResult:
            user_link = LmsUserLink.objects.filter(platform=platform, user=user).first() or LmsUserLink(
                platform=platform, user=user
            )
            if not user_link.external_user_id:
                user_link.external_user_id = connector.ensure_user(platform, user)
            user_link.last_synced_at = timezone.now()
            user_link.save()
            connector.enroll(platform, str(link.external_course_id), user_link.external_user_id, role)
            return {"external_user_id": user_link.external_user_id, "role": role}

        self.log.run(
            platform,
            SyncOperation.ENROLLMENT_ADD,
            {
                "section_id": link.section_id,
                "enrollment_id": getattr(enrollment, "pk", None),
                "user_id": user.pk,
                "payload": {"role": role},
            },
            add,
        )

    def remove_member(self, platform: LmsPlatform, link: LmsCourseLink, user: Any, enrollment: Any = None) -> None:
        connector = self.registry.for_platform(platform)

        def remove() -> StepResult:
            user_link = LmsUserLink.objects.filter(platform=platform, user=user).first()
            if user_link is None or link.external_course_id is None:
                return "not linked"
            connector.unenroll(platform, link.external_course_id, user_link.external_user_id)
            return {"external_user_id": user_link.external_user_id}

        self.log.run(
            platform,
            SyncOperation.ENROLLMENT_REMOVE,
            {"section_id": link.section_id, "enrollment_id": getattr(enrollment, "pk", None), "user_id": user.pk},
            remove,
        )
