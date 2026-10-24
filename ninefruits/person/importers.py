"""Student and instructor CSV imports (original ``StudentImporter``, ``InstructorImporter`` and
``ImportsPersonColumns``). Registered with ``ninefruits.importing.registry`` (types ``students``
and ``instructors``) for the admin screens and ``manage.py reference_import``.

Person columns: ``family_name``, ``given_name``, ``name_{language}`` (name as written in that
language), ``birth_date``, ``gender``, ``email``, ``phone``, ``national_id``. A new row whose
``national_id`` matches an existing person is attached to that person instead of creating a
duplicate (readmission). The person is saved in the row's savepoint, so a row the database
rejects leaves no person behind."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext as _
from django.utils.translation import gettext_lazy

from ninefruits.importing.resources import (
    Column,
    ReferenceResource,
    RowImportFailed,
    attribute_label,
    is_new_record,
    translatable_columns,
)
from ninefruits.organization.models import OrgUnit, Program
from ninefruits.person.enums import EmploymentType, Gender, StudentStatus
from ninefruits.person.models import Instructor, Person, StudentRecord

_PERSON_ATTRIBUTE = "_import_person"


def _person(record: models.Model) -> Person:
    return getattr(record, _PERSON_ATTRIBUTE)


def _set_person(field: str) -> Any:
    def fill(resource: ReferenceResource, record: models.Model, value: Any) -> None:
        if value is not None:
            setattr(_person(record), field, value)

    return fill


def _fill_email(resource: ReferenceResource, record: models.Model, value: Any) -> None:
    if value is None:
        return
    try:
        validate_email(value)
    except ValidationError:
        raise ValidationError(
            _("The %(attribute)s field must be a valid email address.") % {"attribute": "email"}
        ) from None
    _person(record).email = value


def _name_variant_fill(language: str) -> Any:
    def fill(resource: ReferenceResource, record: models.Model, value: Any) -> None:
        if value is not None:
            person = _person(record)
            person.name_variants = {**(person.name_variants or {}), language: value}

    return fill


def person_columns() -> list[Column]:
    from ninefruits.institution.services.supported_locales import SupportedLocales

    def family_name(resource: ReferenceResource, record: models.Model, value: Any) -> None:
        if value is not None:
            _person(record).family_name = value

    return [
        Column("family_name", None, required=is_new_record, max_length=255, fill=family_name),
        Column("given_name", None, max_length=255, fill=_set_person("given_name")),
        *[
            Column(
                f"name_{code}",
                None,
                max_length=255,
                fill=_name_variant_fill(code),
                aliases=tuple(
                    {f"name_{code.replace('-', '_')}", *(["name_zh_CN"] if code == "zh-hans" else [])}
                    - {f"name_{code}"}
                ),
            )
            for code in SupportedLocales().all()
        ],
        Column("birth_date", None, kind="date", fill=_set_person("birth_date")),
        Column("gender", None, choices=Gender, fill=_set_person("gender")),
        Column("email", None, max_length=255, fill=_fill_email),
        Column("phone", None, max_length=32, fill=_set_person("phone")),
        Column("national_id", None, max_length=64, fill=_set_person("national_id_encrypted")),
    ]


def person_for_new_record(row: Mapping[str, Any]) -> Person:
    """The existing person for a new record: matched by national ID when the row has one."""
    national_id = str(row.get("national_id") or "").strip()
    if national_id:
        existing = Person.objects.not_merged().where_pii("national_id", national_id).first()
        if existing is not None:
            return existing
    return Person()


class PersonRecordResource(ReferenceResource):
    """Shared save step: the person first, then the record."""

    class Meta(ReferenceResource.Meta):
        pass

    def before_save_instance(self, instance: models.Model, row: Any, **kwargs: Any) -> None:
        person = _person(instance)
        person.save()
        instance.person = person  # type: ignore[attr-defined]


def _fill_program(resource: ReferenceResource, record: Any, value: Any) -> None:
    if value is None:
        return
    program = Program.objects.filter(code=value).first()
    if program is None:
        raise RowImportFailed(_("No program with the code %(code)s.") % {"code": value})
    record.program = program
    record.org_unit_id = program.org_unit_id


class StudentResource(PersonRecordResource):
    """Initial load and bulk update of student records, matched by ``student_number``.

    Columns: student_number, program (code), admission_date, catalog_year, year_level, status,
    graduation_date, institutional_email, plus the person columns. Status changes made here
    are data corrections: no status change history is written (use the screens or status change
    requests for real changes)."""

    type_key = "students"
    label = gettext_lazy("student records")

    class Meta(PersonRecordResource.Meta):
        model = StudentRecord

    @classmethod
    def columns(cls) -> list[Column]:
        return [
            Column("student_number", "student_number", required_mapping=True, required=True, max_length=32),
            Column("program", None, required=is_new_record, fill=_fill_program),
            Column("admission_date", "admission_date", required=is_new_record, kind="date"),
            Column("catalog_year", "catalog_year", kind="integer", minimum=1900, maximum=2200),
            Column("year_level", "year_level", kind="integer", minimum=1, maximum=10),
            Column("status", "status", choices=StudentStatus),
            Column("graduation_date", "graduation_date", kind="date"),
            Column("institutional_email", None, max_length=255, fill=_fill_institutional_email),
            *person_columns(),
        ]

    def resolve_record(self, row: Mapping[str, Any]) -> StudentRecord:
        number = str(row.get("student_number") or "").strip()
        record = StudentRecord.objects.select_related("person").filter(student_number=number).first()
        if record is None:
            record = StudentRecord(student_number=number)
            setattr(record, _PERSON_ATTRIBUTE, person_for_new_record(row))
        else:
            setattr(record, _PERSON_ATTRIBUTE, record.person)
        return record

    def before_save_instance(self, instance: models.Model, row: Any, **kwargs: Any) -> None:
        super().before_save_instance(instance, row, **kwargs)
        record: StudentRecord = instance  # type: ignore[assignment]
        if record._state.adding:
            if record.catalog_year is None and record.admission_date is not None:
                record.catalog_year = record.admission_date.year
            record.status_changed_at = timezone.now().replace(microsecond=0)


def _fill_institutional_email(resource: ReferenceResource, record: Any, value: Any) -> None:
    if value is None:
        return
    try:
        validate_email(value)
    except ValidationError:
        raise ValidationError(
            _("The %(attribute)s field must be a valid email address.")
            % {"attribute": attribute_label("institutional_email")}
        ) from None
    record.institutional_email = value


class InstructorResource(PersonRecordResource):
    """Columns: employee_number, org_unit (code), employment_type, academic_title_{language},
    hire_date, end_date, plus the person columns. Matched by employee_number."""

    type_key = "instructors"
    label = gettext_lazy("instructors")

    class Meta(PersonRecordResource.Meta):
        model = Instructor

    @classmethod
    def columns(cls) -> list[Column]:
        return [
            Column("employee_number", "employee_number", required_mapping=True, required=True, max_length=32),
            Column("org_unit", "org_unit", required=is_new_record, relation=(OrgUnit, "code")),
            Column("employment_type", "employment_type", required=is_new_record, choices=EmploymentType),
            *translatable_columns("academic_title", required=False),
            Column("hire_date", "hire_date", kind="date"),
            Column("end_date", "end_date", kind="date"),
            *person_columns(),
        ]

    def resolve_record(self, row: Mapping[str, Any]) -> Instructor:
        number = str(row.get("employee_number") or "").strip()
        instructor = Instructor.objects.select_related("person").filter(employee_number=number).first()
        if instructor is None:
            instructor = Instructor(employee_number=number)
            setattr(instructor, _PERSON_ATTRIBUTE, person_for_new_record(row))
        else:
            setattr(instructor, _PERSON_ATTRIBUTE, instructor.person)
        return instructor


def register_importers() -> None:
    from ninefruits.importing import registry
    from ninefruits.security.enums import Permission

    registry.register(StudentResource, Permission.STUDENT_RECORDS_MANAGE)
    registry.register(InstructorResource, Permission.INSTRUCTORS_MANAGE)
