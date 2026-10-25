"""The reporting views (original ``database/sql/views/reporting.sql``, ADR 0016) as unmanaged,
read-only models.

The eight views live in the ``reporting`` schema and are created by the replayed DDL
(``db/schema/2026_10_23_004100_create_reporting_views.sql``), so the models are unmanaged and
use the quoting trick ``db_table = 'reporting"."students'`` (porting-plan 5.3). The views are
``security_invoker``: the row level security of whoever queries applies to the underlying
tables, and the translated text columns (``*_name``, ``course_title``) follow the session
locale (``SET app.locale``, set by ``ninefruits.core.db.session_context``). The jsonb originals
are kept alongside (``*_i18n``). BI tools read the same views through the ``app_reporting``
role.

``visible_to(user)`` gives the application-side answer the row level security gives in the
database: rows of the student records, enrollments and sections the user may see. The views
have no columns of their own to write, so ``save`` and ``delete`` raise."""

from __future__ import annotations

from typing import Any, Self

from django.db import models
from django.utils.translation import gettext_lazy as _

from ninefruits.core.models import VisibleQuerySet


class ReadOnlyViewError(RuntimeError):
    """Raised when code tries to write a reporting view row."""


def _record_ids(user: Any) -> Any:
    from ninefruits.person.models import StudentRecord

    return StudentRecord.objects.visible_to(user).values("pk")


class StudentScopedQuerySet(VisibleQuerySet):
    """Views with one row per student record (or per row of a student record): visible when the
    record is (RLS ``student_records_*`` on the joined ``student_records``)."""

    def visible_to(self, user: Any) -> Self:
        return self.filter(student_record_id__in=_record_ids(user))


class CourseGradeQuerySet(VisibleQuerySet):
    """One row per enrollment: visible when the enrollment is (RLS ``enrollments_*``) and its
    student record is (the view joins ``student_records``)."""

    def visible_to(self, user: Any) -> Self:
        from ninefruits.registration.models import Enrollment

        return self.filter(enrollment_id__in=Enrollment.objects.visible_to(user).values("pk")).filter(
            student_record_id__in=_record_ids(user)
        )


class SectionScopedQuerySet(VisibleQuerySet):
    """One row per section (or meeting). ``sections`` and ``section_meetings`` carry no row level
    security (the course catalog is reference data), so every reader gets every row; only the
    ``enrolled`` and ``waiting`` counts follow the reader's access to enrollments and waitlist
    entries. The application answer is therefore every row as well."""

    def visible_to(self, user: Any) -> Self:
        return self


class HeadcountQuerySet(VisibleQuerySet):
    """Counts per org unit, program, year level and status. The view aggregates the student
    records the caller may see (row level security on ``student_records``), so a group shows
    when at least one of its records is visible; the count in it is the database's."""

    def visible_to(self, user: Any) -> Self:
        from ninefruits.person.models import StudentRecord

        visible = StudentRecord.objects.visible_to(user).filter(
            org_unit_id=models.OuterRef("org_unit_id"),
            program_id=models.OuterRef("program_id"),
            year_level=models.OuterRef("year_level"),
            status=models.OuterRef("status"),
        )
        return self.filter(models.Exists(visible))


class ReportingView(models.Model):
    """Common behaviour of the reporting view models: read only."""

    class Meta:
        abstract = True
        managed = False

    def save(self, *args: Any, **kwargs: Any) -> None:
        raise ReadOnlyViewError(f"Reporting views are read only: {self._meta.db_table}")

    def delete(self, *args: Any, **kwargs: Any) -> Any:
        raise ReadOnlyViewError(f"Reporting views are read only: {self._meta.db_table}")


def _fk(model: str, column: str, verbose_name: Any = None) -> Any:
    """A nullable link to the row behind a view column (no database constraint: views have
    none; view columns are always nullable)."""
    return models.ForeignKey(
        model,
        on_delete=models.DO_NOTHING,
        db_column=column,
        db_constraint=False,
        null=True,
        blank=True,
        related_name="+",
        verbose_name=verbose_name,
    )


class ReportStudent(ReportingView):
    """``reporting.students``: one row per student record with person, program and org unit."""

    student_record_id = models.BigIntegerField(_("Student record"), primary_key=True)
    student_number = models.CharField(_("Student number"), max_length=32, null=True)
    person = _fk("person.Person", "person_id", _("Person"))
    student_name = models.TextField(_("Name"), null=True)
    family_name = models.CharField(max_length=255, null=True)
    given_name = models.CharField(max_length=255, null=True)
    name_variants = models.JSONField(null=True)
    gender = models.CharField(max_length=16, null=True)
    birth_date = models.DateField(null=True)
    program = _fk("organization.Program", "program_id")
    program_code = models.CharField(max_length=64, null=True)
    program_name = models.TextField(null=True)
    program_name_i18n = models.JSONField(null=True)
    org_unit = _fk("organization.OrgUnit", "org_unit_id")
    org_unit_code = models.CharField(max_length=64, null=True)
    org_unit_name = models.TextField(null=True)
    org_unit_name_i18n = models.JSONField(null=True)
    admission_date = models.DateField(null=True)
    catalog_year = models.SmallIntegerField(null=True)
    year_level = models.SmallIntegerField(null=True)
    status = models.CharField(max_length=32, null=True)
    academic_standing = models.CharField(max_length=32, null=True)
    graduation_date = models.DateField(null=True)
    degree_number = models.CharField(max_length=64, null=True)
    institutional_email = models.CharField(max_length=255, null=True)

    objects = StudentScopedQuerySet.as_manager()

    class Meta(ReportingView.Meta):
        db_table = 'reporting"."students'
        verbose_name = _("Students")

    def __str__(self) -> str:
        return str(self.student_number or self.student_record_id)

    def __repr__(self) -> str:
        return f"<ReportStudent {self.student_record_id}>"


class ReportHeadcount(ReportingView):
    """``reporting.headcount``: students per org unit, program, year level and status. The view
    has no single key: the four grouping columns together identify a row (a composite primary
    key cannot be declared because view columns are nullable). ``org_unit_id`` stands in as the
    Django primary key but is not unique, so read this view with ``values()`` (as the report
    catalog does), never by ``pk``."""

    org_unit_id = models.BigIntegerField(primary_key=True)
    org_unit_code = models.CharField(max_length=64, null=True)
    org_unit_name = models.TextField(null=True)
    program_id = models.BigIntegerField(null=True)
    program_code = models.CharField(max_length=64, null=True)
    program_name = models.TextField(null=True)
    year_level = models.SmallIntegerField(null=True)
    status = models.CharField(max_length=32, null=True)
    students = models.BigIntegerField(null=True)

    objects = HeadcountQuerySet.as_manager()

    class Meta(ReportingView.Meta):
        db_table = 'reporting"."headcount'
        verbose_name = _("Headcount")

    def __str__(self) -> str:
        return f"{self.org_unit_code} {self.program_code} {self.year_level} {self.status}"


class ReportTermRecord(ReportingView):
    """``reporting.term_records``: a student's credits, GPA and standing per term."""

    term_record_id = models.BigIntegerField(primary_key=True)
    student_record = _fk("person.StudentRecord", "student_record_id")
    student_number = models.CharField(max_length=32, null=True)
    term = _fk("term.Term", "term_id")
    term_code = models.CharField(max_length=32, null=True)
    term_name = models.TextField(null=True)
    attempted_credits = models.DecimalField(max_digits=5, decimal_places=1, null=True)
    earned_credits = models.DecimalField(max_digits=5, decimal_places=1, null=True)
    term_gpa = models.DecimalField(max_digits=6, decimal_places=3, null=True)
    cumulative_earned_credits = models.DecimalField(max_digits=6, decimal_places=1, null=True)
    cumulative_gpa = models.DecimalField(max_digits=6, decimal_places=3, null=True)
    academic_standing = models.CharField(max_length=32, null=True)
    warning_count = models.IntegerField(null=True)
    is_honors = models.BooleanField(null=True)
    honors_rank = models.IntegerField(null=True)
    closed_at = models.DateTimeField(null=True)

    objects = StudentScopedQuerySet.as_manager()

    class Meta(ReportingView.Meta):
        db_table = 'reporting"."term_records'
        verbose_name = _("Term records")

    def __str__(self) -> str:
        return f"{self.student_number} {self.term_code}"


class ReportCourseGrade(ReportingView):
    """``reporting.course_grades``: one row per enrollment with its grade."""

    enrollment_id = models.BigIntegerField(primary_key=True)
    student_record = _fk("person.StudentRecord", "student_record_id")
    student_number = models.CharField(max_length=32, null=True)
    term_code = models.CharField(max_length=32, null=True)
    term_name = models.TextField(null=True)
    course_code = models.CharField(max_length=32, null=True)
    course_title = models.TextField(null=True)
    course_title_i18n = models.JSONField(null=True)
    section_code = models.CharField(max_length=16, null=True)
    credits = models.DecimalField(max_digits=4, decimal_places=1, null=True)
    course_category = _fk("curriculum.CourseCategory", "course_category_id")
    course_category_name = models.TextField(db_column="course_category", null=True)
    status = models.CharField(max_length=16, null=True)
    grade_status = models.CharField(max_length=16, null=True)
    grade_code = models.CharField(max_length=8, null=True)
    is_passed = models.BooleanField(null=True)
    is_retake = models.BooleanField(null=True)

    objects = CourseGradeQuerySet.as_manager()

    class Meta(ReportingView.Meta):
        db_table = 'reporting"."course_grades'
        verbose_name = _("Course grades")

    def __str__(self) -> str:
        return f"{self.student_number} {self.course_code}"


class ReportSectionEnrollment(ReportingView):
    """``reporting.section_enrollments``: sections with capacity, enrolled, waiting and
    instructors."""

    section_id = models.BigIntegerField(primary_key=True)
    term_code = models.CharField(max_length=32, null=True)
    term_name = models.TextField(null=True)
    course_code = models.CharField(max_length=32, null=True)
    course_title = models.TextField(null=True)
    section_code = models.CharField(max_length=16, null=True)
    org_unit_code = models.CharField(max_length=64, null=True)
    org_unit_name = models.TextField(null=True)
    status = models.CharField(max_length=16, null=True)
    capacity = models.IntegerField(null=True)
    enrolled = models.BigIntegerField(null=True)
    waiting = models.BigIntegerField(null=True)
    instructors = models.TextField(null=True)

    objects = SectionScopedQuerySet.as_manager()

    class Meta(ReportingView.Meta):
        db_table = 'reporting"."section_enrollments'
        verbose_name = _("Section enrollments")

    def __str__(self) -> str:
        return f"{self.course_code}-{self.section_code}"


class ReportSectionMeeting(ReportingView):
    """``reporting.section_meetings``: weekly meetings of sections with their rooms."""

    section_meeting_id = models.BigIntegerField(primary_key=True)
    section_id = models.BigIntegerField(null=True)
    term_code = models.CharField(max_length=32, null=True)
    course_code = models.CharField(max_length=32, null=True)
    course_title = models.TextField(null=True)
    section_code = models.CharField(max_length=16, null=True)
    weekday = models.SmallIntegerField(null=True)
    start_time = models.TimeField(null=True)
    end_time = models.TimeField(null=True)
    start_date = models.DateField(null=True)
    end_date = models.DateField(null=True)
    building_code = models.CharField(max_length=32, null=True)
    room_code = models.CharField(max_length=32, null=True)
    is_active = models.BooleanField(null=True)

    objects = SectionScopedQuerySet.as_manager()

    class Meta(ReportingView.Meta):
        db_table = 'reporting"."section_meetings'
        verbose_name = _("Section meetings")

    def __str__(self) -> str:
        return f"{self.course_code}-{self.section_code} {self.weekday}"


class ReportStatusChange(ReportingView):
    """``reporting.status_changes``: student status changes with their type."""

    status_change_id = models.BigIntegerField(primary_key=True)
    student_record = _fk("person.StudentRecord", "student_record_id")
    student_number = models.CharField(max_length=32, null=True)
    type_code = models.CharField(max_length=64, null=True)
    type_name = models.TextField(null=True)
    from_status = models.CharField(max_length=32, null=True)
    to_status = models.CharField(max_length=32, null=True)
    effective_date = models.DateField(null=True)
    term_code = models.CharField(max_length=32, null=True)
    status = models.CharField(max_length=32, null=True)
    requested_at = models.DateTimeField(null=True)
    decided_at = models.DateTimeField(null=True)

    objects = StudentScopedQuerySet.as_manager()

    class Meta(ReportingView.Meta):
        db_table = 'reporting"."status_changes'
        verbose_name = _("Status changes")

    def __str__(self) -> str:
        return f"{self.student_number} {self.type_code}"


class ReportDegreeAudit(ReportingView):
    """``reporting.degree_audits``: the latest degree audit per student record and program
    role."""

    degree_audit_id = models.BigIntegerField(primary_key=True)
    student_record = _fk("person.StudentRecord", "student_record_id")
    student_number = models.CharField(max_length=32, null=True)
    program_role = models.CharField(max_length=16, null=True)
    program_code = models.CharField(max_length=64, null=True)
    program_name = models.TextField(null=True)
    is_satisfied = models.BooleanField(null=True)
    earned_credits = models.DecimalField(max_digits=5, decimal_places=1, null=True)
    required_credits = models.DecimalField(max_digits=5, decimal_places=1, null=True)
    cumulative_gpa = models.DecimalField(max_digits=4, decimal_places=2, null=True)
    audited_at = models.DateTimeField(null=True)
    term_code = models.CharField(max_length=32, null=True)

    objects = StudentScopedQuerySet.as_manager()

    class Meta(ReportingView.Meta):
        db_table = 'reporting"."degree_audits'
        verbose_name = _("Degree audits")

    def __str__(self) -> str:
        return f"{self.student_number} {self.program_role}"


#: View name -> model, for code that addresses the views by name (ReportCatalog, the API).
VIEW_MODELS: dict[str, type[ReportingView]] = {
    "students": ReportStudent,
    "headcount": ReportHeadcount,
    "term_records": ReportTermRecord,
    "course_grades": ReportCourseGrade,
    "section_enrollments": ReportSectionEnrollment,
    "section_meetings": ReportSectionMeeting,
    "status_changes": ReportStatusChange,
    "degree_audits": ReportDegreeAudit,
}

__all__ = [
    "VIEW_MODELS",
    "ReadOnlyViewError",
    "ReportCourseGrade",
    "ReportDegreeAudit",
    "ReportHeadcount",
    "ReportSectionEnrollment",
    "ReportSectionMeeting",
    "ReportStatusChange",
    "ReportStudent",
    "ReportTermRecord",
    "ReportingView",
]
