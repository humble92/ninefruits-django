"""Final scores from the platform mapped to enrollments (original ``PullGrades``). They are only a
draft: the instructor loads them into the grade entry screen, checks and saves; saving,
submission and finalization follow the grade workflow (ADR 0011).

Where the scores come from: the connector's ``final_scores`` (pull). A platform that sends its
scores instead (``POST /api/v1/lms/platforms/<code>/scores/``) leaves them in the sync log as a
``grades.delivered`` step; when the connector reports none, the latest delivery for the section
is used."""

from __future__ import annotations

from typing import Any

from django.core.exceptions import PermissionDenied

from ninefruits.core.db import session_context
from ninefruits.lms.connectors import ConnectorRegistry, connectors
from ninefruits.lms.enums import LinkStatus, SyncOperation, SyncStatus
from ninefruits.lms.models import LmsCourseLink, LmsPlatform, LmsSyncLog, LmsUserLink
from ninefruits.lms.services.sync_logger import StepResult, SyncLogger

from .sync_section import account_of, enrolled


def delivered_scores(platform: LmsPlatform, section_id: int) -> dict[str, float]:
    """The latest scores the platform delivered for the section (external user id -> score)."""
    log = (
        LmsSyncLog.objects.filter(
            platform=platform,
            section_id=section_id,
            operation=SyncOperation.GRADES_DELIVERED,
            status=SyncStatus.SUCCEEDED,
        )
        .order_by("-started_at", "-id")
        .first()
    )
    scores = (log.payload or {}).get("scores") if log is not None else None
    return {str(key): float(value) for key, value in scores.items()} if isinstance(scores, dict) else {}


def pulls_scores(section: Any) -> bool:
    """Whether an active platform pulling final scores has the section linked (the grade entry
    button is shown)."""
    return LmsCourseLink.objects.filter(
        section_id=section.pk,
        status=LinkStatus.LINKED,
        platform__is_active=True,
        platform__should_pull_grades=True,
    ).exists()


class PullGrades:
    def __init__(self, registry: ConnectorRegistry | None = None, log: SyncLogger | None = None) -> None:
        self.registry = registry or connectors()
        self.log = log or SyncLogger()

    def __call__(self, platform: LmsPlatform, section: Any, actor: Any = None) -> dict[int, float]:
        return self.handle(platform, section, actor)

    def handle(self, platform: LmsPlatform, section: Any, actor: Any = None) -> dict[int, float]:
        """Enrollment id -> score. ``actor``: importing scores is grade entry, so the actor must
        be allowed to enter the section's grades now (instructor in the grade entry window, or
        staff with ``grades.manage`` in scope)."""
        if actor is not None:
            from ninefruits.grading.actions import SaveGrades

            if not SaveGrades().can_enter(section, actor):
                raise PermissionDenied

        link = LmsCourseLink.objects.filter(platform=platform, section_id=section.pk).first()
        if link is None or link.external_course_id is None or not platform.should_pull_grades:
            return {}

        connector = self.registry.for_platform(platform)
        scores: dict[int, float] = {}

        def pull() -> StepResult:
            by_external = connector.final_scores(platform, str(link.external_course_id)) or delivered_scores(
                platform, section.pk
            )
            users = dict(
                LmsUserLink.objects.filter(platform=platform, external_user_id__in=list(by_external)).values_list(
                    "user_id", "external_user_id"
                )
            )
            for enrollment in enrolled(section.pk):
                user = account_of(enrollment.student_record.person)
                external = users.get(user.pk) if user is not None else None
                if external is not None and external in by_external:
                    scores[enrollment.pk] = float(by_external[external])
            return {"scores": len(scores), "reported": len(by_external)}

        # The actor is authorized by the section; the log and the user links are platform data.
        with session_context().system("lms.pull_grades"):
            self.log.run(platform, SyncOperation.GRADES_PULL, {"section_id": section.pk}, pull)
        return scores
