"""Writes ``registration_attempts``: every attempt with each rule's result (original
``AttemptLog``)."""

from __future__ import annotations

from typing import Any

from django.utils import timezone

from ninefruits.core import context as request_context
from ninefruits.registration.data import RuleEvaluation
from ninefruits.registration.enums import AttemptAction, AttemptOutcome


class AttemptLog:
    def record(
        self,
        record: Any,
        section: Any,
        action: AttemptAction,
        outcome: AttemptOutcome,
        evaluation: RuleEvaluation,
        actor: Any,
    ) -> Any:
        from ninefruits.registration.models import RegistrationAttempt

        return RegistrationAttempt.objects.create(
            student_record_id=record.pk,
            term_id=getattr(section, "term_id", None),
            section_id=getattr(section, "pk", None),
            action=AttemptAction(action),
            outcome=AttemptOutcome(outcome),
            results=evaluation.to_list(),
            actor_id=getattr(actor, "pk", None),
            request_id=request_context.current().request_id,
            attempted_at=timezone.now().replace(microsecond=0),
        )
