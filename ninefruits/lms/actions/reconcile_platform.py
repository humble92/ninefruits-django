"""The nightly full comparison (original ``ReconcilePlatform``): for every published section of
the terms not yet ended (or one term), the course exists and its members on the platform match
the roster; missing members are added, extra ones removed, and the differences are logged. Events
can be missed (queue or platform outage), so this is the safety net; both paths use the same
``SyncSection.member`` / ``remove_member``."""

from __future__ import annotations

from typing import Any, TypedDict

from django.utils import timezone

from ninefruits.lms.connectors import ConnectorRegistry, connectors
from ninefruits.lms.enums import INSTRUCTOR, STUDENT, LinkStatus, SyncOperation
from ninefruits.lms.models import LmsCourseLink, LmsPlatform, LmsUserLink
from ninefruits.lms.services.sync_logger import StepResult, SyncLogger

from .sync_section import SyncSection, account_of, enrolled, instructor_accounts


class ReconcileSummary(TypedDict):
    sections: int
    added: int
    removed: int
    failed: int


def current_sections(term: Any = None) -> Any:
    """Published sections of the term, or of every term that has not ended."""
    from ninefruits.offering.enums import SectionStatus
    from ninefruits.offering.models import Section

    sections = Section.objects.filter(status=SectionStatus.PUBLISHED).select_related("course", "term", "session")
    if term is not None:
        return sections.filter(term_id=term.pk)
    return sections.filter(term__end_date__gte=timezone.localdate())


class ReconcilePlatform:
    def __init__(
        self,
        registry: ConnectorRegistry | None = None,
        sections: SyncSection | None = None,
        log: SyncLogger | None = None,
    ) -> None:
        self.registry = registry or connectors()
        self.sections = sections or SyncSection(self.registry)
        self.log = log or SyncLogger()

    def __call__(self, platform: LmsPlatform, term: Any = None, dry_run: bool = False) -> ReconcileSummary:
        return self.handle(platform, term, dry_run)

    def handle(self, platform: LmsPlatform, term: Any = None, dry_run: bool = False) -> ReconcileSummary:
        summary: ReconcileSummary = {"sections": 0, "added": 0, "removed": 0, "failed": 0}
        for section in list(current_sections(term).order_by("pk")):
            summary["sections"] += 1
            try:
                self._reconcile(platform, section, dry_run, summary)
            except Exception:
                summary["failed"] += 1
        return summary

    def _reconcile(self, platform: LmsPlatform, section: Any, dry_run: bool, summary: ReconcileSummary) -> None:
        link = LmsCourseLink.objects.filter(platform=platform, section=section).first()
        if link is None or link.status != LinkStatus.LINKED:
            self.sections.handle(platform, section, dry_run)
            return

        connector = self.registry.for_platform(platform)
        expected = self._expected_members(platform, section)
        actual = connector.members(platform, str(link.external_course_id))
        missing = [external for external in expected if external not in actual]
        extra = [external for external in actual if external not in expected]

        def fix() -> StepResult:
            for external in missing:
                user, role, enrollment = expected[external]
                self.sections.member(platform, link, user, role, enrollment)
                summary["added"] += 1
            for external in extra:
                user_link = (
                    LmsUserLink.objects.filter(platform=platform, external_user_id=external)
                    .select_related("user")
                    .first()
                )
                if user_link is not None:
                    self.sections.remove_member(platform, link, user_link.user)
                    summary["removed"] += 1
            return {"missing": missing, "extra": extra}

        self.log.run(
            platform,
            SyncOperation.RECONCILE,
            {"section_id": section.pk, "payload": {"missing": missing, "extra": extra}},
            fix,
            dry_run,
            atomic=False,
        )

    def _expected_members(self, platform: LmsPlatform, section: Any) -> dict[str, tuple[Any, str, Any]]:
        """External user id -> (user, role, enrollment or ``None``) for everyone who should be in
        the course."""
        connector = self.registry.for_platform(platform)
        links = dict(LmsUserLink.objects.filter(platform=platform).values_list("user_id", "external_user_id"))
        expected: dict[str, tuple[Any, str, Any]] = {}
        for user in instructor_accounts(section):
            expected[links.get(user.pk) or connector.ensure_user(platform, user)] = (user, INSTRUCTOR, None)
        for enrollment in enrolled(section.pk):
            user = account_of(enrollment.student_record.person)
            if user is not None:
                expected[links.get(user.pk) or connector.ensure_user(platform, user)] = (user, STUDENT, enrollment)
        return expected
