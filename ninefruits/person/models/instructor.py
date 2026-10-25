"""Teaching staff record of a person (original ``App\\Models\\Person\\Instructor``, legacy
FACULTY). One per person.

Other apps reference it as ``"person.Instructor"`` (section instructors, advisors)."""

from __future__ import annotations

from datetime import date
from typing import Self

from django.db import models
from django.db.models import Q
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from ninefruits.core.models import TimeStampedModel, VisibleQuerySet
from ninefruits.i18n.fields import TranslatableJSONField
from ninefruits.person.enums import EmploymentType


class InstructorQuerySet(VisibleQuerySet):
    def current(self, on: date | None = None) -> Self:
        """Employed on the date (today by default)."""
        on = on or timezone.localdate()
        return self.filter(Q(end_date__isnull=True) | Q(end_date__gte=on))


class Instructor(TimeStampedModel):
    person = models.OneToOneField(
        "person.Person", on_delete=models.RESTRICT, related_name="instructor", verbose_name=_("Person")
    )
    employee_number = models.CharField(_("Employee number"), max_length=32, unique=True)
    org_unit = models.ForeignKey(
        "organization.OrgUnit", on_delete=models.RESTRICT, related_name="instructors", verbose_name=_("Org unit")
    )
    employment_type = models.CharField(_("Employment type"), max_length=32, choices=EmploymentType.choices)
    academic_title = TranslatableJSONField(_("Academic title"), null=True, blank=True)
    hire_date = models.DateField(_("Hire date"), null=True, blank=True)
    end_date = models.DateField(_("End date"), null=True, blank=True)

    objects = InstructorQuerySet.as_manager()

    class Meta:
        db_table = "instructors"
        ordering = ["employee_number"]
        verbose_name = _("instructor")
        verbose_name_plural = _("instructors")

    def __str__(self) -> str:
        return f"{self.person.display_name()} ({self.employee_number})"

    def __repr__(self) -> str:
        return f"<Instructor {self.pk} {self.employee_number}>"

    def is_current(self, on: date | None = None) -> bool:
        """Employed on the date (today by default)."""
        return self.end_date is None or self.end_date >= (on or timezone.localdate())
