"""Emails students who have course evaluations open and not done (original
``evaluation:remind``)."""

from __future__ import annotations

from typing import Any

from django.core.management.base import CommandParser

from ninefruits.core.commands import AuditedCommand
from ninefruits.evaluation.notifications import send_evaluation_reminder
from ninefruits.evaluation.services import EvaluationTasks
from ninefruits.term.models import Term


class Command(AuditedCommand):
    help = "Email students who have course evaluations open and not done"

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument("term", help="Term code")
        parser.add_argument("--dry-run", action="store_true", help="Count the students without sending")

    def handle(self, *args: Any, **options: Any) -> int:  # type: ignore[override]  # exit code (StatusCommand)
        from ninefruits.person.models import StudentRecord
        from ninefruits.registration.enums import EnrollmentStatus
        from ninefruits.registration.models import Enrollment

        term = Term.objects.filter(code=options["term"]).first()
        if term is None:
            self.error("Unknown term code.")
            return self.FAILURE

        tasks = EvaluationTasks()
        record_ids = (
            Enrollment.objects.filter(
                term_id=term.pk, status__in=[EnrollmentStatus.ENROLLED, EnrollmentStatus.COMPLETED]
            )
            .values("student_record_id")
            .distinct()
        )
        students = 0
        sent = 0
        records = StudentRecord.objects.filter(pk__in=record_ids).select_related("person__user").order_by("pk")
        for record in records.iterator(chunk_size=500):
            pending = [enrollment for enrollment in tasks.pending(record) if enrollment.term_id == term.pk]
            if not pending:
                continue
            students += 1
            user = getattr(record.person, "user", None)
            if not self.is_dry_run() and user is not None and send_evaluation_reminder(user, pending):
                sent += 1

        self.record_result({"students": students, "sent": sent})
        self.info(f"{students} student(s) with evaluations to do, {sent} reminder(s) sent.")
        return self.SUCCESS
