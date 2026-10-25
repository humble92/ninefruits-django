"""Degree audits, requirement waivers and degree number sequences (original
``App\\Models\\Graduation\\{DegreeAudit, DegreeRequirementWaiver}``, ADR 0016).

The tables come from the replayed schema (``db/schema/2026_10_23_004000_create_graduation_tables``)
with their row level security (``db/sql/policies/graduation.sql``): audits and waivers are read by
whoever sees the student record, audits are written with ``graduation.audit`` and waivers with
``graduation.process`` (or in the system context)."""

from __future__ import annotations

from typing import Any, Self

from django.db import models
from django.db.models import Max
from django.utils.translation import gettext_lazy as _
from django.utils.translation import pgettext_lazy

from ninefruits.core.models import TimeStampedModel, VisibleQuerySet
from ninefruits.curriculum.enums import ProgramRole
from ninefruits.graduation.enums import WaiverStatus


def _visible_record_ids(user: Any) -> Any:
    from ninefruits.person.models import StudentRecord

    return StudentRecord.objects.visible_to(user).values("pk")


class DegreeAuditQuerySet(VisibleQuerySet):
    def visible_to(self, user: Any) -> Self:
        """Audits of the student records the user may see (``degree_audits_record_select``)."""
        return self.filter(student_record_id__in=_visible_record_ids(user))

    def newest_per_student(self) -> Self:
        """The newest audit per student record and program role (original
        ``scopeNewestPerStudent``; the ``reporting.degree_audits`` view uses the same rule)."""
        newest = (
            DegreeAudit.objects.order_by()
            .values("student_record_id", "program_role")
            .annotate(newest=Max("id"))
            .values("newest")
        )
        return self.filter(pk__in=newest)

    def primary(self) -> Self:
        return self.filter(program_role=ProgramRole.PRIMARY)


class DegreeAudit(TimeStampedModel):
    """A stored degree audit: what the student had achieved against the requirement set at that
    moment. Graduation is processed from the latest stored audit."""

    student_record = models.ForeignKey(
        "person.StudentRecord",
        on_delete=models.RESTRICT,
        related_name="degree_audits",
        verbose_name=_("Student record"),
    )
    requirement_set = models.ForeignKey(
        "curriculum.CurriculumRequirementSet",
        on_delete=models.RESTRICT,
        null=True,
        blank=True,
        db_column="curriculum_requirement_set_id",
        related_name="degree_audits",
        verbose_name=_("graduation requirements"),
    )
    program_role = models.CharField(_("Program role"), max_length=16, choices=ProgramRole.choices)
    program = models.ForeignKey(
        "organization.Program",
        on_delete=models.RESTRICT,
        related_name="degree_audits",
        verbose_name=pgettext_lazy("graduation", "Program"),
    )
    term = models.ForeignKey(
        "term.Term", on_delete=models.RESTRICT, null=True, blank=True, related_name="+", verbose_name=_("Term")
    )
    is_satisfied = models.BooleanField(_("Satisfied"))
    earned_credits = models.DecimalField(pgettext_lazy("graduation", "Earned credits"), max_digits=5, decimal_places=1)
    required_credits = models.DecimalField(
        pgettext_lazy("graduation", "Required"), max_digits=5, decimal_places=1, null=True, blank=True
    )
    cumulative_gpa = models.DecimalField(
        pgettext_lazy("grading", "Cumulative GPA"), max_digits=4, decimal_places=2, null=True, blank=True
    )
    #: The whole evaluation (``DegreeAuditResult.to_dict()``): requirements, issues, courses.
    result = models.JSONField()
    audited_at = models.DateTimeField(_("Audited"))
    audited_by = models.ForeignKey("security.User", on_delete=models.SET_NULL, null=True, blank=True, related_name="+")

    objects = DegreeAuditQuerySet.as_manager()

    class Meta:
        db_table = "degree_audits"
        ordering = ["-audited_at", "-id"]
        verbose_name = _("Degree audit")
        verbose_name_plural = _("Degree audits")

    def __str__(self) -> str:
        return f"{self.student_record_id} {self.program_role} {self.audited_at:%Y-%m-%d}"

    def __repr__(self) -> str:
        return f"<DegreeAudit {self.pk} record={self.student_record_id} role={self.program_role}>"


class DegreeRequirementWaiverQuerySet(VisibleQuerySet):
    def visible_to(self, user: Any) -> Self:
        """Waivers of the student records the user may see
        (``degree_requirement_waivers_record_select``)."""
        return self.filter(student_record_id__in=_visible_record_ids(user))

    def approved(self) -> Self:
        return self.filter(status=WaiverStatus.APPROVED)

    def pending(self) -> Self:
        return self.filter(status=WaiverStatus.PENDING)


class DegreeRequirementWaiver(TimeStampedModel):
    """A requirement waived for one student (transfer credit, change of major): requested with a
    reason, approved by someone else, and possibly lifted later. The audit counts a waiver only
    while it is approved. One open (pending or approved) waiver per record and requirement
    (``degree_requirement_waivers_open_unique``)."""

    student_record = models.ForeignKey(
        "person.StudentRecord",
        on_delete=models.CASCADE,
        related_name="requirement_waivers",
        verbose_name=_("Student record"),
    )
    requirement = models.ForeignKey(
        "curriculum.CurriculumRequirement",
        on_delete=models.CASCADE,
        db_column="curriculum_requirement_id",
        related_name="waivers",
        verbose_name=_("Requirements"),
    )
    reason = models.TextField(pgettext_lazy("common", "Reason"))
    status = models.CharField(
        pgettext_lazy("graduation", "Status"),
        max_length=16,
        choices=WaiverStatus.choices,
        default=WaiverStatus.PENDING,
    )
    requested_by = models.ForeignKey(
        "security.User", on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )
    requested_at = models.DateTimeField(pgettext_lazy("grading", "Requested"))
    decided_by = models.ForeignKey("security.User", on_delete=models.SET_NULL, null=True, blank=True, related_name="+")
    decided_at = models.DateTimeField(null=True, blank=True)
    decision_note = models.TextField(pgettext_lazy("grading", "Note"), null=True, blank=True)
    lifted_by = models.ForeignKey("security.User", on_delete=models.SET_NULL, null=True, blank=True, related_name="+")
    lifted_at = models.DateTimeField(null=True, blank=True)
    lift_reason = models.TextField(_("Lift reason"), null=True, blank=True)

    objects = DegreeRequirementWaiverQuerySet.as_manager()

    class Meta:
        db_table = "degree_requirement_waivers"
        ordering = ["-requested_at", "-id"]
        verbose_name = _("Requirement waiver")
        verbose_name_plural = _("Requirement waivers")

    def __str__(self) -> str:
        return f"{self.student_record_id} · {self.requirement_id}"

    def __repr__(self) -> str:
        return f"<DegreeRequirementWaiver {self.pk} record={self.student_record_id} status={self.status}>"

    @property
    def curriculum_requirement_id(self) -> int:
        return int(self.requirement_id)


class DegreeNumberSequence(models.Model):
    """The last degree number issued per prefix (advanced by ``DegreeNumberGenerator`` with one
    atomic upsert)."""

    prefix = models.CharField(max_length=64, primary_key=True)
    last_value = models.BigIntegerField(default=0)
    created_at = models.DateTimeField(null=True, blank=True)
    updated_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "degree_number_sequences"

    def __str__(self) -> str:
        return f"{self.prefix}: {self.last_value}"


__all__ = ["DegreeAudit", "DegreeNumberSequence", "DegreeRequirementWaiver"]
