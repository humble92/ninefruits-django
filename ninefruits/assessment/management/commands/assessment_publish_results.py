"""Publishes the results of a session to the students (original ``assessment:publish-results``), as
the admin screen does. Requires ``--actor``."""

from __future__ import annotations

from typing import Any

from django.core.exceptions import PermissionDenied, ValidationError
from django.core.management.base import CommandParser

from ninefruits.assessment.actions import RecordAssessmentResult
from ninefruits.assessment.models import AssessmentResult
from ninefruits.core.commands import AuditedCommand

from .assessment_import_results import find_session


class Command(AuditedCommand):
    help = "Publish the results of a session to the students, as the admin screen does. Requires --actor."

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument("type", help="Kind code")
        parser.add_argument("held_date", help="Session date (YYYY-MM-DD)")

    def handle(self, *args: Any, **options: Any) -> int:  # type: ignore[override]  # exit code (StatusCommand)
        session = find_session(options["type"], options["held_date"])
        actor = self.actor()
        if session is None or actor is None:
            self.error(
                "Unknown session: give the kind code and the session date."
                if session is None
                else "--actor is required."
            )
            return self.FAILURE
        try:
            RecordAssessmentResult().publish(session, actor)
        except ValidationError as error:
            self.error(" ".join(str(message) for message in error.messages))
            return self.FAILURE
        except PermissionDenied:
            self.error("The --actor account may not publish results (assessments.record).")
            return self.FAILURE
        count = AssessmentResult.objects.filter(session_id=session.pk).count()
        self.record_result({"session_id": session.pk, "results": count})
        self.info(f"Published {count} result(s) of {session.label()}.")
        return self.SUCCESS
