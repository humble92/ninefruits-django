"""Advisor assignments (original ``AssignAdvisor``)."""

from __future__ import annotations

from datetime import date, timedelta
from typing import Any

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils.translation import gettext as _

from ninefruits.audit.logger import audit
from ninefruits.person.enums import AdvisorRole
from ninefruits.person.models import AdvisorAssignment, Instructor, StudentRecord


class AssignAdvisor:
    """Assigns an advisor from a date. A new primary advisor ends the current one the day
    before, so the history shows who advised when."""

    def handle(
        self,
        record: StudentRecord,
        instructor: Instructor,
        start_date: date,
        role: AdvisorRole | str = AdvisorRole.PRIMARY,
        assigned_by: Any = None,
    ) -> AdvisorAssignment:
        role = AdvisorRole(role)
        if not instructor.is_current():
            raise ValidationError({"instructor_id": _("This instructor is not currently employed.")})

        with transaction.atomic():
            if role == AdvisorRole.PRIMARY:
                for current in record.advisor_assignments.filter(role=AdvisorRole.PRIMARY, end_date__isnull=True):
                    current.end_date = (
                        current.start_date if current.start_date >= start_date else start_date - timedelta(days=1)
                    )
                    current.save(update_fields=["end_date", "updated_at"])

            assignment = AdvisorAssignment.objects.create(
                student_record=record, instructor=instructor, role=role, start_date=start_date
            )
            audit(
                "advisor.assigned",
                assignment,
                properties={"student_record_id": record.pk, "instructor_id": instructor.pk, "role": role.value},
                causer=assigned_by,
            )
        return assignment

    __call__ = handle
