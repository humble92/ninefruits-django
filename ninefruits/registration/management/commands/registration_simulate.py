"""Explains, rule by rule, whether a student could register for a section now (or at ``--at``),
without registering and without an attempt log entry (original ``registration:simulate``). For
"why can I not register?" questions."""

from __future__ import annotations

import io
from typing import Any

from django.core.management.base import CommandParser
from django.utils import timezone
from rich.console import Console
from rich.table import Table

from ninefruits.core.commands import StatusCommand
from ninefruits.core.db import session_context
from ninefruits.offering.models import Section
from ninefruits.person.models import StudentRecord
from ninefruits.registration.data import RegistrationContext
from ninefruits.registration.enums import AttemptAction, RuleSeverity
from ninefruits.registration.services.rule_engine import RegistrationRuleEngine
from ninefruits.registration.services.seat_allocator import SeatAllocator
from ninefruits.term.management.commands.term_inspect import parse_moment


class Command(StatusCommand):
    help = "Explain the registration rules for a student and a section without registering"

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument("student_number", metavar="student-number", help="Student number")
        parser.add_argument("section", help="Section as COURSE-SECTION, e.g. CSE2010-01")
        parser.add_argument("--term", help="Term code (default: the section's latest term)")
        parser.add_argument("--at", help='Time to judge, e.g. "2027-02-10 10:00 Asia/Seoul"')

    def handle(self, *args: Any, **options: Any) -> int:  # type: ignore[override]  # exit code (StatusCommand)
        with session_context().system("command:registration_simulate"):
            return self._simulate(options)

    def _simulate(self, options: dict[str, Any]) -> int:
        record = StudentRecord.objects.filter(student_number=options["student_number"]).first()
        course_code, _dash, section_code = str(options["section"]).partition("-")
        sections = Section.objects.filter(course__code=course_code, section_code=section_code)
        if options.get("term"):
            sections = sections.filter(term__code=options["term"])
        section = sections.select_related("course", "term").order_by("-term__start_date").first()
        if record is None or section is None:
            self.error("Unknown student number." if record is None else "Unknown section.")
            return self.FAILURE

        at = timezone.now()
        if options.get("at"):
            parsed = parse_moment(str(options["at"]))
            if parsed is None:
                self.error(f"Cannot read the time [{options['at']}].")
                return self.FAILURE
            at = parsed

        evaluation = RegistrationRuleEngine().evaluate(RegistrationContext(record, section, AttemptAction.ENROLL, at))
        seat = SeatAllocator().find(section, record, at)

        table = Table("Rule", "Result", "Severity", "Message")
        for result in evaluation.results:
            outcome = "pass" if result.passed else ("overridden" if result.overridden else "FAIL")
            table.add_row(result.code.value, outcome, RuleSeverity(result.severity).value, str(result.message or ""))
        if seat is None:
            seat_text = "No seat for this student"
        elif isinstance(seat, str):
            seat_text = "General seat"
        else:
            seat_text = f"Reserved seat: {seat.name}"
        table.add_row("capacity", "FAIL" if seat is None else "pass", "block", seat_text)
        buffer = io.StringIO()
        Console(file=buffer, width=160, force_terminal=False, color_system=None).print(table)
        self.stdout.write(buffer.getvalue().rstrip("\n"))

        blocked = evaluation.is_blocked() or seat is None
        if blocked:
            self.warn("Would be refused.")
            return self.PROBLEMS_FOUND
        self.info("Would be registered.")
        return self.SUCCESS
