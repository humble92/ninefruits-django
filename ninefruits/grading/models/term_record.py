"""Term records (original ``App\\Models\\Grading\\TermRecord``, ADR 0011): a student's credits, GPA
and standing for a term, with cumulative values up to that term (the legacy computed these live
in views). Calculated from finalized grades (``TermRecordCalculator``); term close makes it the
official snapshot (``closed_at``). The GPA columns are unconstrained ``numeric`` so a GPA keeps
the decimals it was calculated with."""

from __future__ import annotations

from typing import Any, Self

from django.db import models
from django.utils.translation import gettext_lazy as _
from django.utils.translation import pgettext_lazy

from ninefruits.core.models import TimeStampedModel, VisibleQuerySet
from ninefruits.grading.enums import AcademicStanding


def gpa_field(verbose_name: Any) -> models.DecimalField:  # type: ignore[type-arg]
    """The GPA columns are ``numeric`` without precision; Django does not round on the way in or
    out, so the declared precision only describes the largest values (0 to 10, 3 decimals)."""
    return models.DecimalField(verbose_name, max_digits=6, decimal_places=3, null=True, blank=True)


class TermRecordQuerySet(VisibleQuerySet):
    def visible_to(self, user: Any) -> Self:
        """Records of student records the user can see (RLS ``term_records_record_select``), all
        for global ``grades.manage`` (``term_records_staff_all``)."""
        from ninefruits.registration.models.enrollment import visible_record_ids
        from ninefruits.security.enums import Permission
        from ninefruits.security.services.authorization import authorization

        if (
            user is not None
            and getattr(user, "is_authenticated", False)
            and authorization().scope_for(user, Permission.GRADES_MANAGE).is_global
        ):
            return self
        return self.filter(student_record_id__in=visible_record_ids(user))


class TermRecord(TimeStampedModel):
    student_record = models.ForeignKey(
        "person.StudentRecord", on_delete=models.RESTRICT, related_name="term_records", verbose_name=_("student record")
    )
    term = models.ForeignKey(
        "term.Term", on_delete=models.RESTRICT, related_name="term_records", verbose_name=_("term")
    )
    attempted_credits = models.DecimalField(_("Attempted credits"), max_digits=5, decimal_places=1, default=0)
    earned_credits = models.DecimalField(
        pgettext_lazy("grading", "Earned credits"), max_digits=5, decimal_places=1, default=0
    )
    gpa_credits = models.DecimalField(max_digits=5, decimal_places=1, default=0)
    grade_points_total = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    term_gpa = gpa_field(_("Term GPA"))
    cumulative_attempted_credits = models.DecimalField(max_digits=6, decimal_places=1, default=0)
    cumulative_earned_credits = models.DecimalField(max_digits=6, decimal_places=1, default=0)
    cumulative_gpa_credits = models.DecimalField(max_digits=6, decimal_places=1, default=0)
    cumulative_grade_points_total = models.DecimalField(max_digits=9, decimal_places=2, default=0)
    cumulative_gpa = gpa_field(pgettext_lazy("grading", "Cumulative GPA"))
    academic_standing = models.CharField(
        _("Academic standing"), max_length=32, choices=AcademicStanding.choices, null=True, blank=True
    )
    warning_count = models.IntegerField(_("Warnings"), default=0)
    is_honors = models.BooleanField(pgettext_lazy("grading", "Honors"), default=False)
    honors_rank = models.IntegerField(pgettext_lazy("grading", "Honors rank"), null=True, blank=True)
    calculated_at = models.DateTimeField()
    closed_at = models.DateTimeField(pgettext_lazy("grading", "Closed"), null=True, blank=True)

    objects = TermRecordQuerySet.as_manager()

    class Meta:
        db_table = "term_records"
        ordering = ["term_id", "student_record_id"]
        verbose_name = _("term record")
        verbose_name_plural = _("term records")
        constraints = [
            models.UniqueConstraint(
                fields=["student_record", "term"], name="term_records_student_record_id_term_id_unique"
            ),
        ]

    def __str__(self) -> str:
        return f"{self.student_record_id}:{self.term_id}"

    def __repr__(self) -> str:
        return f"<TermRecord {self.pk} record={self.student_record_id} term={self.term_id}>"

    @property
    def standing(self) -> AcademicStanding | None:
        return AcademicStanding(self.academic_standing) if self.academic_standing else None
