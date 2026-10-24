"""Bulk matriculation of confirmed applicants (original ``admission:matriculate``), the same as
the admin list's bulk action. Each applicant is done in its own transaction, so one failure does
not stop the rest."""

from __future__ import annotations

from typing import Any

from django.core.exceptions import PermissionDenied, ValidationError
from django.core.management.base import CommandParser

from ninefruits.admission.actions import MatriculateApplicant
from ninefruits.admission.enums import ApplicationStatus
from ninefruits.admission.models import AdmissionCycle, Application
from ninefruits.core.commands import AuditedCommand
from ninefruits.term.models import Term


class Command(AuditedCommand):
    help = "Create student records for confirmed applicants of a cycle. Requires --term and --actor."

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument("cycle", help="Admission cycle code")
        parser.add_argument("--term", help="Admission term code, e.g. 2027-SP (required)")
        parser.add_argument(
            "--dry-run", action="store_true", help="List the applicants without creating student records"
        )

    def handle(self, *args: Any, **options: Any) -> int:
        cycle = AdmissionCycle.objects.filter(code=options["cycle"]).first()
        term = Term.objects.filter(code=options.get("term") or "").first()
        actor = self.actor()
        if cycle is None or term is None:
            self.error("Unknown cycle or --term.")
            return self.FAILURE
        if actor is None:
            self.error("--actor is required: matriculation is recorded under that account and limited to its scope.")
            return self.FAILURE

        applications = list(
            Application.objects.filter(
                admission_cycle=cycle, status=ApplicationStatus.CONFIRMED, student_record__isnull=True
            )
            .select_related("person", "program", "admission_cycle")
            .order_by("application_number")
        )
        self.record_result({"cycle": cycle.code, "term": term.code, "candidates": len(applications)})

        if self.is_dry_run():
            for application in applications:
                self.stdout.write(
                    f"  {application.application_number}  {application.person.romanized_name()}  "
                    f"{application.program.code}"
                )
            self.info(f"Dry run: {len(applications)} confirmed applicant(s) would be matriculated into {term.code}.")
            return self.SUCCESS

        matriculate = MatriculateApplicant()
        created: list[str] = []
        failed: list[str | None] = []
        for application in applications:
            try:
                record = matriculate.handle(application, term, actor)
            except ValidationError as error:
                failed.append(application.application_number)
                self.stdout.write(f"  failed {application.application_number}: {error.messages[0]}")
            except PermissionDenied:
                failed.append(application.application_number)
                self.stdout.write(f"  failed {application.application_number}: not in your scope")
            else:
                created.append(record.student_number)
                self.stdout.write(f"  created {application.application_number} -> {record.student_number}")

        self.record_result({"created": len(created), "failed": failed})
        self.info(f"{len(created)} student record(s) created, {len(failed)} failed.")
        return self.SUCCESS if not failed else self.PROBLEMS_FOUND
