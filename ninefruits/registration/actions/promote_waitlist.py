"""Gives free seats to waiting students in request order (original ``PromoteWaitlist``,
porting-plan 10.7).

Each promotion is a full registration: every rule is checked again, so a student who no longer
qualifies (credit limit reached meanwhile, time conflict, hold) is taken off the list with the
reason, and the next one is tried. A student who only lacks a seat they qualify for (the rest
is reserved) keeps waiting. When neither registration nor add/drop is open for the section any
more, the remaining entries expire. Students are notified by email either way.

Promotions run as the system (the attempt log records no actor); callers authorize first."""

from __future__ import annotations

from typing import Any

from django.utils import timezone
from django.utils.translation import gettext as _

from ninefruits.core.db import session_context
from ninefruits.offering.models import Section
from ninefruits.registration.data import EnrollOptions
from ninefruits.registration.enums import AttemptAction, EnrollmentSource, WaitlistStatus
from ninefruits.registration.models import WaitlistEntry
from ninefruits.registration.notifications import send_waitlist_outcome
from ninefruits.registration.services.seat_allocator import SeatAllocator
from ninefruits.term.enums import TermWindowType
from ninefruits.term.services import TermResolver

from .enroll_student import EnrollStudent, now


class PromoteWaitlist:
    def __init__(
        self,
        enroll: EnrollStudent | None = None,
        seats: SeatAllocator | None = None,
        terms: TermResolver | None = None,
    ) -> None:
        self.enroll = enroll or EnrollStudent()
        self.seats = seats or SeatAllocator()
        self.terms = terms or TermResolver()

    def __call__(self, section: Section) -> dict[str, int]:
        return self.handle(section)

    def handle(self, section: Section) -> dict[str, int]:
        with session_context().system("registration.promote_waitlist"):
            return self._promote(section)

    def _promote(self, section: Section) -> dict[str, int]:
        counts = {"promoted": 0, "removed": 0, "expired": 0}
        at = timezone.now()
        if not self._enrollment_open(section, at):
            for entry in self._waiting(section):
                self._resolve(entry, WaitlistStatus.EXPIRED, _("Registration closed before a seat became free."))
                counts["expired"] += 1
            return counts

        for entry in self._waiting(section):
            section.refresh_from_db()
            if self.seats.availability(section, timezone.now()).is_full():
                break
            outcome = self.enroll.handle(
                entry.student_record,
                section,
                None,
                EnrollOptions(source=EnrollmentSource.WAITLIST),
                AttemptAction.PROMOTE,
            )
            if outcome.succeeded():
                counts["promoted"] += 1
                entry.refresh_from_db()
                send_waitlist_outcome(entry, WaitlistStatus.PROMOTED, None)
            elif not outcome.refused_for_seat():
                self._resolve(entry, WaitlistStatus.REMOVED, " ".join(outcome.messages()))
                counts["removed"] += 1
        return counts

    def _waiting(self, section: Section) -> list[WaitlistEntry]:
        return list(
            WaitlistEntry.objects.filter(section_id=section.pk, status=WaitlistStatus.WAITING)
            .select_related("student_record__person__user", "section__course", "section__version")
            .order_by("requested_at", "id")
        )

    def _enrollment_open(self, section: Section, at: Any) -> bool:
        return any(
            w.term_id == section.term_id for w in self.terms.open_windows(TermWindowType.REGISTRATION, at)
        ) or any(w.session_id == section.session_id for w in self.terms.open_windows(TermWindowType.ADD_DROP, at))

    def _resolve(self, entry: WaitlistEntry, status: WaitlistStatus, note: str) -> None:
        entry.status = status
        entry.resolved_at = now()
        entry.outcome_note = note
        entry.save(update_fields=["status", "resolved_at", "outcome_note", "updated_at"])
        send_waitlist_outcome(entry, status, note)
