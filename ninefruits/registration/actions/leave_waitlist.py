"""A student leaves a waitlist, or staff remove them with a reason (original ``LeaveWaitlist``)."""

from __future__ import annotations

from typing import Any

from django.core.exceptions import PermissionDenied, ValidationError
from django.utils.translation import gettext as _

from ninefruits.registration.enums import WaitlistStatus
from ninefruits.registration.models import WaitlistEntry

from .enroll_student import is_own, now


class LeaveWaitlist:
    def __call__(self, entry: WaitlistEntry, actor: Any, reason: str | None = None) -> WaitlistEntry:
        return self.handle(entry, actor, reason)

    def handle(self, entry: WaitlistEntry, actor: Any, reason: str | None = None) -> WaitlistEntry:
        own = is_own(actor, entry.student_record)
        if not own and not entry.section.is_registration_manageable_by(actor):
            raise PermissionDenied
        if entry.status != WaitlistStatus.WAITING:
            raise ValidationError({"status": _("This waitlist entry is no longer waiting.")})
        entry.status = WaitlistStatus.REMOVED
        entry.resolved_at = now()
        entry.outcome_note = _("You left the waitlist.") if own else reason
        entry.save(update_fields=["status", "resolved_at", "outcome_note", "updated_at"])
        return entry
