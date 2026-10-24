"""Advisor of a student record for a period (original ``AdvisorAssignment``, legacy
SR_ADVISER, LEADING_PROFESSOR). One open primary advisor per record (partial unique index
``advisor_assignments_single_primary_unique``). No row level security on this table: the
student record policies refer to it (ADR 0007)."""

from __future__ import annotations

from datetime import date
from typing import Self

from django.db import models
from django.db.models import Q
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.utils.translation import pgettext_lazy

from ninefruits.core.models import TimeStampedModel, VisibleQuerySet
from ninefruits.person.enums import AdvisorRole


class AdvisorAssignmentQuerySet(VisibleQuerySet):
    def current(self, on: date | None = None) -> Self:
        """Assignments in effect on the date (today by default)."""
        on = on or timezone.localdate()
        return self.filter(start_date__lte=on).filter(Q(end_date__isnull=True) | Q(end_date__gte=on))


class AdvisorAssignment(TimeStampedModel):
    student_record = models.ForeignKey(
        "person.StudentRecord", on_delete=models.CASCADE, related_name="advisor_assignments"
    )
    instructor = models.ForeignKey(
        "person.Instructor",
        on_delete=models.RESTRICT,
        related_name="advisor_assignments",
        verbose_name=pgettext_lazy("people", "Advisor"),
    )
    role = models.CharField(_("Advisor role"), max_length=32, choices=AdvisorRole.choices, default=AdvisorRole.PRIMARY)
    start_date = models.DateField(_("Start date"))
    end_date = models.DateField(_("End date"), null=True, blank=True)

    objects = AdvisorAssignmentQuerySet.as_manager()

    class Meta:
        db_table = "advisor_assignments"
        ordering = ["-start_date", "-id"]
        verbose_name = _("advisor")
        verbose_name_plural = _("advisors")

    def __str__(self) -> str:
        return f"{self.instructor} ({self.get_role_display()})"

    def __repr__(self) -> str:
        return f"<AdvisorAssignment {self.pk} record={self.student_record_id}>"

    def is_current(self, on: date | None = None) -> bool:
        on = on or timezone.localdate()
        return self.start_date <= on and (self.end_date is None or self.end_date >= on)
