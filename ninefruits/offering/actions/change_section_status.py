from __future__ import annotations

from typing import Any

from django.core.exceptions import PermissionDenied, ValidationError
from django.utils.translation import gettext as _

from ninefruits.audit.logger import audit
from ninefruits.core.events import dispatch
from ninefruits.offering.enums import SectionStatus
from ninefruits.offering.events import SectionPublished
from ninefruits.offering.models import Section
from ninefruits.offering.services import ScheduleConflicts


class ChangeSectionStatus:
    """Publishes a section (visible in the course catalog), cancels it (reason required; its
    meetings free their rooms and instructors) or takes it back to draft. Reopening a cancelled
    section checks its rooms and instructors again."""

    def __init__(self, conflicts: ScheduleConflicts | None = None) -> None:
        self.conflicts = conflicts or ScheduleConflicts()

    def __call__(self, section: Section, status: SectionStatus | str, user: Any, reason: str | None = None) -> Section:
        if not section.is_manageable_by(user):
            raise PermissionDenied
        status = SectionStatus(status)
        if section.status == status:
            return section
        if status == SectionStatus.CANCELLED and not (reason or "").strip():
            raise ValidationError({"reason": _("Give a reason.")})

        previous = SectionStatus(section.status)

        def change() -> None:
            section.status = status
            section.save(update_fields=["status", "updated_at"])

        try:
            self.conflicts.guard(change, "status")
        except Exception:
            section.status = previous
            raise
        audit(
            f"section.{status.value}",
            section,
            reason=reason,
            properties={"previous_status": previous.value},
            causer=user,
        )
        if status == SectionStatus.PUBLISHED:
            dispatch(SectionPublished(section))
        return section
