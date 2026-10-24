"""Recalculates term records (credits and GPA) from finalized grades (original
``grades:recalculate``), e.g. after a grading policy change. Standing and honors stay as decided
at term close."""

from __future__ import annotations

from typing import Any

from django.core.exceptions import ValidationError
from django.core.management.base import CommandParser

from ninefruits.core.commands import AuditedCommand
from ninefruits.grading.actions import RecalculateTermRecords
from ninefruits.person.models import StudentRecord
from ninefruits.term.models import Term


class Command(AuditedCommand):
    help = "Recalculate term records (credits and GPA) from finalized grades, e.g. after a grading policy change"

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument("--term", help="Term code: students with grades in it, from that term on")
        parser.add_argument("--student-number", help="One student")
        parser.add_argument("--reason", help="Why (required)")

    def handle(self, *args: Any, **options: Any) -> int:
        term = Term.objects.filter(code=options["term"]).first() if options.get("term") else None
        record = (
            StudentRecord.objects.filter(student_number=options["student_number"]).first()
            if options.get("student_number")
            else None
        )
        if (options.get("term") and term is None) or (options.get("student_number") and record is None):
            self.error("Unknown term code or student number.")
            return self.FAILURE
        try:
            count = RecalculateTermRecords().handle(term, record, options.get("reason") or "", self.actor())
        except ValidationError:
            self.error("--reason is required.")
            return self.FAILURE
        self.record_result({"students": count})
        self.info(f"{count} student(s) recalculated. Standing and honors stay as decided at term close.")
        return self.SUCCESS
