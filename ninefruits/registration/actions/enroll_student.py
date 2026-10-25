"""Registers a student for a section (original ``EnrollStudent``, porting-plan 10.7, ADR 0010).

All rules first, outside any lock (every reason is reported), then a seat taken under the
section's row lock. With no seat the student can join the waitlist. Every attempt is logged with
its rule results. The student registers themselves; staff with ``registration.manage`` for the
section may register anyone and waive rules that allow it, with a reason. Waitlist promotion
calls this with no actor (system)."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from django.core.exceptions import PermissionDenied, ValidationError
from django.db import IntegrityError, transaction
from django.utils import timezone
from django.utils.translation import gettext as _

from ninefruits.audit.logger import audit
from ninefruits.core.db import session_context
from ninefruits.core.events import dispatch
from ninefruits.offering.models import Section, SectionSeatGroup
from ninefruits.registration.data import EnrollOptions, RegistrationContext, RegistrationOutcome, RuleEvaluation
from ninefruits.registration.enums import AttemptAction, AttemptOutcome, EnrollmentSource, RuleCode, WaitlistStatus
from ninefruits.registration.events import EnrollmentConfirmed
from ninefruits.registration.models import CartItem, Enrollment, WaitlistEntry
from ninefruits.registration.rules.duplicate_course import duplicate_message
from ninefruits.registration.services.attempt_log import AttemptLog
from ninefruits.registration.services.rule_engine import RegistrationRuleEngine
from ninefruits.registration.services.seat_allocator import SeatAllocator
from ninefruits.registration.services.waitlists import position as waitlist_position
from ninefruits.registration.services.waitlists import waiting_counts

UNIQUE_VIOLATION = "23505"


def now() -> datetime:
    """Whole seconds: the columns are ``timestamptz(0)``."""
    return timezone.now().replace(microsecond=0)


def reason_required() -> ValidationError:
    return ValidationError({"reason": _("Enter a reason.")})


def full_message(waitlist_open: bool) -> str:
    if waitlist_open:
        return _("The section is full. You can join the waitlist.")
    return _("The section is full.")


def is_own(actor: Any, record: Any) -> bool:
    person_id = getattr(actor, "person_id", None)
    return person_id is not None and person_id == record.person_id


class EnrollStudent:
    def __init__(
        self,
        engine: RegistrationRuleEngine | None = None,
        seats: SeatAllocator | None = None,
        attempts: AttemptLog | None = None,
    ) -> None:
        self.engine = engine or RegistrationRuleEngine()
        self.seats = seats or SeatAllocator()
        self.attempts = attempts or AttemptLog()

    def __call__(
        self,
        record: Any,
        section: Section,
        actor: Any,
        options: EnrollOptions | None = None,
        action: AttemptAction = AttemptAction.ENROLL,
    ) -> RegistrationOutcome:
        return self.handle(record, section, actor, options, action)

    def handle(
        self,
        record: Any,
        section: Section,
        actor: Any,
        options: EnrollOptions | None = None,
        action: AttemptAction = AttemptAction.ENROLL,
    ) -> RegistrationOutcome:
        options = options or EnrollOptions()
        by_staff = self._authorize(record, section, actor, options)
        at = now()

        evaluation = self.engine.evaluate(
            RegistrationContext(record, section, action, at, actor, by_staff, tuple(options.waive))
        )
        if evaluation.is_blocked():
            self.attempts.record(record, section, action, AttemptOutcome.REFUSED, evaluation, actor)
            return RegistrationOutcome(AttemptOutcome.REFUSED, evaluation)

        retake_of = evaluation.detail("repeats_enrollment_id")
        try:
            with transaction.atomic():
                outcome = self._take_seat(record, section, actor, options, evaluation, at, by_staff, retake_of)
        except IntegrityError as error:
            if getattr(error.__cause__, "sqlstate", None) != UNIQUE_VIOLATION:
                raise
            # A parallel request of the same student got there first.
            outcome = RegistrationOutcome(
                AttemptOutcome.REFUSED,
                evaluation.with_result(RuleCode.DUPLICATE_COURSE, duplicate_message(section.label())),
            )

        logged_action = AttemptAction.WAITLIST if outcome.outcome == AttemptOutcome.WAITLISTED else action
        self.attempts.record(record, section, logged_action, outcome.outcome, outcome.evaluation, actor)

        if by_staff and outcome.enrollment is not None:
            audit(
                "enrollment.staff_enrolled",
                outcome.enrollment,
                reason=options.reason,
                properties={
                    "waived": [str(code.value) for code in options.waive],
                    "warnings": outcome.evaluation.warnings(),
                },
                causer=actor,
            )
        return outcome

    def _take_seat(
        self,
        record: Any,
        section: Section,
        actor: Any,
        options: EnrollOptions,
        evaluation: RuleEvaluation,
        at: datetime,
        by_staff: bool,
        retake_of: int | None,
    ) -> RegistrationOutcome:
        locked = self.seats.lock(section.pk)
        seat = self.seats.find(locked, record, at)
        if seat is None:
            return self._full(record, locked, actor, options, evaluation, at)

        version = locked.version
        source = options.source or (EnrollmentSource.STAFF if by_staff else EnrollmentSource.STUDENT)
        enrollment = Enrollment.objects.create(
            student_record_id=record.pk,
            section_id=locked.pk,
            term_id=locked.term_id,
            course_id=locked.course_id,
            version_id=locked.version_id,
            credits=version.credits,
            category_id=version.category_id,
            counts_toward_credit_limit=version.counts_toward_credit_limit,
            seat_group_id=seat.pk if isinstance(seat, SectionSeatGroup) else None,
            is_retake=retake_of is not None,
            repeats_enrollment_id=retake_of,
            source=source,
            enrolled_at=at,
            changed_by_id=getattr(actor, "pk", None),
        )
        self.seats.take(locked, seat)

        # Bookkeeping of the student's own rows (cart, waitlist): the caller is authorized, and
        # the student's own policies do not let them mark an entry promoted.
        with session_context().system("registration.enroll"):
            CartItem.objects.filter(student_record_id=record.pk, section_id=locked.pk).delete()
            WaitlistEntry.objects.filter(
                student_record_id=record.pk, section_id=locked.pk, status=WaitlistStatus.WAITING
            ).update(status=WaitlistStatus.PROMOTED, resolved_at=at, enrollment_id=enrollment.pk, updated_at=at)

        dispatch(EnrollmentConfirmed(enrollment))
        return RegistrationOutcome(AttemptOutcome.SUCCEEDED, evaluation, enrollment)

    def _full(
        self,
        record: Any,
        section: Section,
        actor: Any,
        options: EnrollOptions,
        evaluation: RuleEvaluation,
        at: datetime,
    ) -> RegistrationOutcome:
        waiting = waiting_counts([section.pk]).get(section.pk, 0)
        if not options.waitlist_if_full or section.waitlist_capacity <= waiting:
            message = full_message(section.waitlist_capacity > waiting)
            return RegistrationOutcome(AttemptOutcome.REFUSED, evaluation.with_result(RuleCode.CAPACITY, message))

        entry = WaitlistEntry.objects.filter(
            section_id=section.pk, student_record_id=record.pk, status=WaitlistStatus.WAITING
        ).first() or WaitlistEntry.objects.create(
            section_id=section.pk,
            student_record_id=record.pk,
            requested_at=at,
            requested_by_id=getattr(actor, "pk", None),
        )
        message = _("You are on the waitlist (position %(position)s).") % {"position": waitlist_position(entry)}
        return RegistrationOutcome(
            AttemptOutcome.WAITLISTED,
            evaluation.with_result(RuleCode.CAPACITY, message, passed=True),
            waitlist_entry=entry,
        )

    def _authorize(self, record: Any, section: Section, actor: Any, options: EnrollOptions) -> bool:
        """Whether staff act for the student."""
        if actor is None:
            return False  # system: waitlist promotion
        if is_own(actor, record) and not options.waive:
            return False
        if not section.is_registration_manageable_by(actor):
            raise PermissionDenied
        if not (options.reason or "").strip():
            raise reason_required()
        return True
