"""Student records (original ``App\\Models\\Person\\StudentRecord`` and
``StudentRecordProgram``, ADR 0007).

One row is one admission of a person, with a new student number each time. Graduation changes
the status instead of moving the row (legacy SRREGISTRY -> SGREGISTRY). The status changes only
through ``student_status_changes`` (``RequestStatusChange``/``DecideStatusChange``/
``RecordStatusChange``)."""

from __future__ import annotations

from datetime import date
from typing import Any, Self

from django.db import models
from django.db.models import Q
from django.db.models.expressions import RawSQL
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.utils.translation import pgettext_lazy

from ninefruits.core.models import TimeStampedModel, VisibleQuerySet
from ninefruits.person.enums import AdditionalProgramRequestStatus, AdditionalProgramRole, StudentStatus
from ninefruits.security.enums import Permission

# Students in the sections the user teaches (roster, attendance, grades); the same query as
# util.taught_student_record_ids() but for the given person. The tables come from the replayed
# schema, their models from Phases 4 and 5.
_TAUGHT_RECORD_IDS_SQL = (
    "SELECT e.student_record_id FROM enrollments AS e "
    "JOIN section_instructors AS si ON si.section_id = e.section_id "
    "JOIN instructors AS i ON i.id = si.instructor_id "
    "WHERE i.person_id = %s AND e.status IN ('enrolled', 'completed')"
)


def _scope_for(user: Any, permission: Permission) -> Any:
    from ninefruits.security.services.authorization import authorization

    return authorization().scope_for(user, permission)


class StudentRecordQuerySet(VisibleQuerySet):
    def active(self) -> Self:
        return self.filter(status__in=StudentStatus.active())

    def visible_to(self, user: Any) -> Self:
        """Records the user may see: staff by scope (``student_records.view`` or ``.manage``:
        all, org unit and below, program, including second majors and minors in that scope),
        records behind second major or minor requests they decide, the student's own records,
        current advisees and students in the sections they teach. Mirrors the row level
        security policies on ``student_records``."""
        scope = _scope_for(user, Permission.STUDENT_RECORDS_VIEW).merge(
            _scope_for(user, Permission.STUDENT_RECORDS_MANAGE)
        )
        if scope.is_global:
            return self

        condition = Q(pk__in=[])
        if scope.org_unit_ids:
            condition |= Q(org_unit_id__in=scope.org_unit_ids)
        if scope.program_ids:
            condition |= Q(program_id__in=scope.program_ids)
        if scope.org_unit_ids or scope.program_ids:
            condition |= Q(
                pk__in=StudentRecordProgram.objects.filter(end_date__isnull=True)
                .filter(Q(program_id__in=scope.program_ids) | Q(program__org_unit_id__in=scope.org_unit_ids))
                .values("student_record_id")
            )

        from .additional_program import AdditionalProgramRequest

        condition |= Q(
            pk__in=AdditionalProgramRequest.objects.filter(status=AdditionalProgramRequestStatus.REQUESTED)
            .decidable_by(user)
            .values("student_record_id")
        )

        if user.person_id is not None:
            from .advisor import AdvisorAssignment

            condition |= Q(person_id=user.person_id)
            condition |= Q(
                pk__in=AdvisorAssignment.objects.current()
                .filter(instructor__person_id=user.person_id)
                .values("student_record_id")
            )
            condition |= Q(pk__in=RawSQL(_TAUGHT_RECORD_IDS_SQL, [user.person_id]))  # noqa: S611 - constant SQL  # nosec B611
        return self.filter(condition)


class StudentRecord(TimeStampedModel):
    person = models.ForeignKey(
        "person.Person", on_delete=models.RESTRICT, related_name="student_records", verbose_name=_("Person")
    )
    student_number = models.CharField(_("Student number"), max_length=32, unique=True)
    program = models.ForeignKey(
        "organization.Program",
        on_delete=models.RESTRICT,
        related_name="student_records",
        verbose_name=pgettext_lazy("security", "Program"),
    )
    org_unit = models.ForeignKey(
        "organization.OrgUnit", on_delete=models.RESTRICT, related_name="student_records", verbose_name=_("Org unit")
    )
    admission_term = models.ForeignKey(
        "term.Term",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
        verbose_name=_("Admission term"),
    )
    admission_type = models.ForeignKey(
        "institution.LookupValue",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
        verbose_name=_("Admission type"),
    )
    admission_date = models.DateField(_("Admission date"))
    catalog_year = models.SmallIntegerField(_("Catalog year"))
    year_level = models.SmallIntegerField(pgettext_lazy("people", "Year"), default=1)
    status = models.CharField(
        pgettext_lazy("people", "Status"), max_length=32, choices=StudentStatus.choices, default=StudentStatus.ENROLLED
    )
    status_changed_at = models.DateTimeField(null=True, blank=True)
    academic_standing = models.CharField(max_length=32, null=True, blank=True)
    graduation_date = models.DateField(_("Graduation date"), null=True, blank=True)
    degree_number = models.CharField(max_length=64, null=True, blank=True, unique=True)
    institutional_email = models.CharField(_("School email"), max_length=255, null=True, blank=True)
    tags = models.JSONField(_("Tags"), null=True, blank=True)

    objects = StudentRecordQuerySet.as_manager()

    class Meta:
        db_table = "student_records"
        ordering = ["-admission_date", "-id"]
        verbose_name = _("student record")
        verbose_name_plural = _("student records")

    def __str__(self) -> str:
        return self.student_number

    def __repr__(self) -> str:
        return f"<StudentRecord {self.pk} {self.student_number}>"

    @property
    def student_status(self) -> StudentStatus:
        return StudentStatus(self.status)

    def is_visible_to(self, user: Any) -> bool:
        return StudentRecord.objects.visible_to(user).filter(pk=self.pk).exists()

    def is_manageable_by(self, user: Any) -> bool:
        """``student_records.manage`` in a scope that covers the record."""
        scope = _scope_for(user, Permission.STUDENT_RECORDS_MANAGE)
        return scope.is_global or self.org_unit_id in scope.org_unit_ids or self.program_id in scope.program_ids

    def current_programs(self) -> models.QuerySet[StudentRecordProgram]:
        return self.additional_programs.filter(end_date__isnull=True)

    # -- TargetSubject (ADR 0006) -------------------------------------------------------------
    def target_program_ids(self) -> list[int]:
        return [self.program_id, *self.current_programs().values_list("program_id", flat=True)]

    def target_org_unit_ids(self) -> list[int]:
        """The record's unit and the units of its current second majors and minors, with their
        ancestors (eligibility for "students of the College of Engineering" includes them)."""
        from ninefruits.organization.models import OrgUnit

        units = list(
            dict.fromkeys([self.org_unit_id, *self.current_programs().values_list("program__org_unit_id", flat=True)])
        )
        ids: list[int] = []
        for unit in OrgUnit.objects.filter(pk__in=units):
            for ancestor in unit.ancestor_ids():
                if ancestor not in ids:
                    ids.append(ancestor)
        return ids

    def target_admission_year(self) -> int | None:
        return self.admission_date.year

    def target_year_level(self) -> int | None:
        return self.year_level

    def target_student_status(self) -> str | None:
        return str(self.status)

    def target_academic_standing(self) -> str | None:
        return self.academic_standing

    def target_tags(self) -> list[str]:
        return [str(tag) for tag in (self.tags or [])]


class StudentRecordProgramQuerySet(VisibleQuerySet):
    def current(self) -> Self:
        return self.filter(end_date__isnull=True)


class StudentRecordProgram(TimeStampedModel):
    """A second major or minor of a student record. The primary program is on the record."""

    student_record = models.ForeignKey(StudentRecord, on_delete=models.CASCADE, related_name="additional_programs")
    program = models.ForeignKey(
        "organization.Program",
        on_delete=models.RESTRICT,
        related_name="+",
        verbose_name=pgettext_lazy("security", "Program"),
    )
    role = models.CharField(pgettext_lazy("people", "Kind"), max_length=32, choices=AdditionalProgramRole.choices)
    start_date = models.DateField(_("Start date"))
    end_date = models.DateField(_("End date"), null=True, blank=True)

    objects = StudentRecordProgramQuerySet.as_manager()

    class Meta:
        db_table = "student_record_programs"
        ordering = ["start_date", "id"]
        verbose_name = _("second major or minor")
        verbose_name_plural = _("second majors and minors")

    def __str__(self) -> str:
        return f"{self.program} ({self.get_role_display()})"

    def __repr__(self) -> str:
        return f"<StudentRecordProgram {self.pk} record={self.student_record_id}>"

    def is_current(self, on: date | None = None) -> bool:
        return self.end_date is None or self.end_date >= (on or timezone.localdate())


class StudentNumberSequence(models.Model):
    """Per-prefix counter of the student number generator (``StudentNumberGenerator``)."""

    prefix = models.CharField(max_length=64, primary_key=True)
    last_value = models.BigIntegerField(default=0)
    created_at = models.DateTimeField(null=True, blank=True, default=timezone.now, editable=False)
    updated_at = models.DateTimeField(null=True, blank=True, auto_now=True, editable=False)

    objects = VisibleQuerySet.as_manager()

    class Meta:
        db_table = "student_number_sequences"

    def __str__(self) -> str:
        return self.prefix
