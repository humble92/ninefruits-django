"""Emails instructors whose sections still have grades not submitted (original
``grades:remind-missing``)."""

from __future__ import annotations

from collections import defaultdict
from typing import Any

from django.core.management.base import CommandParser
from django.db.models import Exists, OuterRef

from ninefruits.core.commands import AuditedCommand
from ninefruits.grading.enums import GradeStatus
from ninefruits.grading.notifications import send_missing_grades
from ninefruits.offering.models import Section, SectionInstructor
from ninefruits.term.models import Term


class Command(AuditedCommand):
    help = "Email instructors whose sections still have grades not submitted"

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument("term", help="Term code")
        parser.add_argument("--dry-run", action="store_true", help="List the instructors without sending")

    def handle(self, *args: Any, **options: Any) -> int:  # type: ignore[override]  # exit code (StatusCommand)
        from ninefruits.registration.enums import EnrollmentStatus
        from ninefruits.registration.models import Enrollment

        term = Term.objects.filter(code=options["term"]).first()
        if term is None:
            self.error("Unknown term code.")
            return self.FAILURE

        missing = Enrollment.objects.filter(
            section_id=OuterRef("pk"),
            status=EnrollmentStatus.ENROLLED,
            grade_status__in=[GradeStatus.NONE, GradeStatus.DRAFT],
        )
        sections = list(
            Section.objects.filter(term_id=term.pk)
            .filter(Exists(missing))
            .select_related("course", "version")
            .order_by("course__code", "section_code")
        )
        by_instructor: dict[int, list[Section]] = defaultdict(list)
        instructors: dict[int, Any] = {}
        assignments = SectionInstructor.objects.filter(section__in=sections).select_related("instructor__person__user")
        labels = {section.pk: section for section in sections}
        for assignment in assignments.order_by("instructor_id", "section_id"):
            instructors[assignment.instructor_id] = assignment.instructor
            by_instructor[assignment.instructor_id].append(labels[assignment.section_id])

        sent = 0
        for instructor_id, mine in by_instructor.items():
            instructor = instructors[instructor_id]
            self.stdout.write(f"{instructor.person.display_name()}: {', '.join(s.label() for s in mine)}")
            user = getattr(instructor.person, "user", None)
            if not self.is_dry_run() and user is not None and send_missing_grades(user, mine):
                sent += 1

        self.record_result({"sections": len(sections), "instructors": len(by_instructor), "sent": sent})
        self.info(
            f"{len(sections)} section(s) with missing grades, {len(by_instructor)} instructor(s), "
            f"{sent} reminder(s) sent."
        )
        return self.SUCCESS
