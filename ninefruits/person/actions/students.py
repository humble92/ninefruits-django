"""Registering student records (original ``RegisterStudent``)."""

from __future__ import annotations

from datetime import date
from typing import Any

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone
from django.utils.dateparse import parse_date
from django.utils.translation import gettext as _

from ninefruits.audit.logger import audit
from ninefruits.organization.models import Program
from ninefruits.person.models import Person, StudentRecord
from ninefruits.person.services.student_numbers import StudentNumberGenerator, student_number_exists


class RegisterStudent:
    """Creates a student record (one admission) for a person, with a new student number unless
    one is given. A person who studied before keeps their person row and account; only the
    record is new (porting-plan 10.1). Phase 3 matriculation uses this.

    ``details``: ``admission_date`` (required), ``catalog_year``, ``year_level``,
    ``admission_term_id``, ``admission_type_id``, ``institutional_email``, ``student_number``,
    ``tags``."""

    def __init__(self, numbers: StudentNumberGenerator | None = None) -> None:
        self._numbers = numbers

    def handle(
        self, person: Person, program: Program, details: dict[str, Any], registered_by: Any = None
    ) -> StudentRecord:
        if person.merged_into_id is not None:
            raise ValidationError(
                {"person_id": _("This person was merged into another person. Use that person instead.")}
            )

        admission_date = details["admission_date"]
        if isinstance(admission_date, str):
            admission_date = parse_date(admission_date)
        if not isinstance(admission_date, date):
            raise ValidationError({"admission_date": _("Enter a valid date.")})

        if not program.is_effective_on(admission_date):
            raise ValidationError({"program_id": _("The program is not in effect on the admission date.")})

        with transaction.atomic():
            number = str(details.get("student_number") or "").strip()
            if not number:
                number = (self._numbers or StudentNumberGenerator()).next(admission_date.year)
            if student_number_exists(number):
                raise ValidationError({"student_number": _("This student number is already used.")})

            record = StudentRecord.objects.create(
                person=person,
                student_number=number,
                program=program,
                org_unit_id=program.org_unit_id,
                admission_date=admission_date,
                catalog_year=details.get("catalog_year") or admission_date.year,
                year_level=details.get("year_level") or 1,
                admission_term_id=details.get("admission_term_id"),
                admission_type_id=details.get("admission_type_id"),
                institutional_email=details.get("institutional_email") or None,
                tags=details.get("tags") or None,
                status_changed_at=timezone.now(),
            )
            audit(
                "student_record.registered",
                record,
                properties={"person_id": person.pk, "student_number": number, "program": program.code},
                causer=registered_by,
            )
        return record

    __call__ = handle
