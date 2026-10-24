"""Staff review and the applicant's answer (original ``DecideApplication``,
``ReleaseDecisions`` and ``RespondToOffer``)."""

from __future__ import annotations

from collections.abc import Iterable
from datetime import timedelta
from typing import Any

from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.utils import timezone
from django.utils.translation import gettext as _

from ninefruits.admission.enums import ApplicationStatus
from ninefruits.admission.models import Application
from ninefruits.audit.logger import audit
from ninefruits.security.enums import Permission


def ensure_reviewer(application: Application, reviewer: Any) -> None:
    if not application.is_in_scope_of(reviewer, Permission.APPLICATIONS_REVIEW):
        raise PermissionDenied


def _invalid_transition() -> ValidationError:
    return ValidationError({"status": _("This is not possible in the application's current status.")})


class DecideApplication:
    """Review steps by admissions staff (``applications.review`` in scope): start the review,
    then admit or reject. A decision can be changed until it is released to the applicant.
    Cycles that release decisions immediately notify the applicant at once."""

    def __init__(self, release: ReleaseDecisions | None = None) -> None:
        self.release = release or ReleaseDecisions()

    def start_review(self, application: Application, reviewer: Any) -> Application:
        ensure_reviewer(application, reviewer)
        if application.status != ApplicationStatus.SUBMITTED:
            raise _invalid_transition()
        application.status = ApplicationStatus.UNDER_REVIEW
        application.review_started_at = timezone.now()
        application.save(update_fields=["status", "review_started_at", "updated_at"])
        audit("application.review_started", application, causer=reviewer)
        return application

    def admit(self, application: Application, reviewer: Any, note: str | None = None) -> Application:
        return self._decide(application, ApplicationStatus.ADMITTED, reviewer, note)

    def reject(self, application: Application, reviewer: Any, note: str) -> Application:
        return self._decide(application, ApplicationStatus.REJECTED, reviewer, note)

    def _decide(
        self, application: Application, decision: ApplicationStatus, reviewer: Any, note: str | None
    ) -> Application:
        ensure_reviewer(application, reviewer)
        if not application.is_decision_changeable():
            raise _invalid_transition()

        with transaction.atomic():
            previous = application.status
            now = timezone.now()
            application.status = decision
            application.decided_by = reviewer
            application.decided_at = now
            application.decision_note = note or None
            application.review_started_at = application.review_started_at or now
            application.save(
                update_fields=["status", "decided_by", "decided_at", "decision_note", "review_started_at", "updated_at"]
            )
            audit(
                f"application.{decision.value}",
                application,
                reason=note or None,
                properties={"previous_status": str(previous)},
                causer=reviewer,
            )

        if application.admission_cycle.should_release_decisions_immediately:
            self.release.handle([application], reviewer)
        return application


class ReleaseDecisions:
    """Makes decisions visible to applicants and emails them. Admitted applicants get an offer
    deadline when the cycle sets response days. Applications not decided, already released or
    outside the user's review scope are skipped."""

    def handle(self, applications: Iterable[Application], released_by: Any) -> int:
        """Returns the number released."""
        from ninefruits.admission.notifications import send_application_decision

        released = 0
        for application in applications:
            if not application.application_status.is_decided() or application.is_decision_visible_to_applicant():
                continue
            if not application.is_in_scope_of(released_by, Permission.APPLICATIONS_REVIEW):
                continue

            now = timezone.now()
            days = application.admission_cycle.offer_response_days
            application.decision_released_at = now
            application.offer_expires_at = (
                now + timedelta(days=days)
                if application.status == ApplicationStatus.ADMITTED and days is not None
                else None
            )
            application.save(update_fields=["decision_released_at", "offer_expires_at", "updated_at"])
            audit(
                "application.decision_released",
                application,
                properties={"decision": str(application.status)},
                causer=released_by,
            )
            transaction.on_commit(lambda application=application: send_application_decision(application))
            released += 1
        return released

    __call__ = handle


class RespondToOffer:
    """An admitted applicant accepts (confirmed: waiting for matriculation) or declines
    (withdrawn) a released offer before its deadline. Staff can record a response received by
    other means, with a reason."""

    def handle(self, application: Application, accept: bool, actor: Any, reason: str | None = None) -> Application:
        own = application.is_owned_by(actor)
        if not own:
            ensure_reviewer(application, actor)
            if not (reason or "").strip():
                raise ValidationError({"reason": _("Give the reason when recording a response for the applicant.")})

        if application.status != ApplicationStatus.ADMITTED or not application.is_decision_visible_to_applicant():
            raise ValidationError({"status": _("There is no offer to answer.")})
        if own and application.offer_expires_at is not None and application.offer_expires_at < timezone.now():
            raise ValidationError(
                {"status": _("The deadline to accept this offer has passed. Contact the admissions office.")}
            )

        now = timezone.now()
        application.responded_at = now
        if accept:
            application.status = ApplicationStatus.CONFIRMED
            fields = ["status", "responded_at", "updated_at"]
        else:
            application.status = ApplicationStatus.WITHDRAWN
            application.withdrawn_at = now
            application.withdrawal_reason = reason or "declined"
            fields = ["status", "responded_at", "withdrawn_at", "withdrawal_reason", "updated_at"]
        application.save(update_fields=fields)
        audit(
            "application.offer_accepted" if accept else "application.offer_declined",
            application,
            reason=reason or None,
            causer=actor,
        )
        return application

    __call__ = handle
