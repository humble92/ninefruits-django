"""Degree or study program offered by an org unit (original ``App\\Models\\Organization\\Program``)."""

from __future__ import annotations

from typing import Any

from django.db import models
from django.utils.translation import gettext_lazy as _
from django.utils.translation import pgettext_lazy

from ninefruits.core.models import EffectivePeriodMixin, EffectiveQuerySet, TimeStampedModel
from ninefruits.i18n.fields import TranslatableJSONField
from ninefruits.organization.enums import DegreeLevel

from .org_unit import OrgUnit


class ProgramQuerySet(EffectiveQuerySet):
    pass


class Program(EffectivePeriodMixin, TimeStampedModel):
    code = models.CharField(pgettext_lazy("reference", "Code"), max_length=64, unique=True)
    name = TranslatableJSONField(pgettext_lazy("reference", "Name"))
    degree_title = TranslatableJSONField(_("Degree title"), null=True, blank=True)
    degree_level = models.CharField(_("Degree level"), max_length=32, choices=DegreeLevel.choices)
    org_unit = models.ForeignKey(
        OrgUnit, on_delete=models.RESTRICT, related_name="programs", verbose_name=_("Org unit")
    )
    standard_duration_years = models.DecimalField(
        _("Standard duration (years)"), max_digits=3, decimal_places=1, null=True, blank=True
    )
    allows_second_major = models.BooleanField(_("Accepts second majors"), default=False)
    allows_minor = models.BooleanField(_("Accepts minors"), default=False)

    objects = ProgramQuerySet.as_manager()

    class Meta:
        db_table = "programs"
        ordering = ["code"]
        verbose_name = _("program")
        verbose_name_plural = _("programs")

    def __str__(self) -> str:
        return f"{self.code} {self.name or ''}".strip()

    def is_additional_program_decidable_by(self, user: Any) -> bool:
        """Whether the user decides second major and minor matters of this program
        (``additional_programs.approve`` in its scope)."""
        from ninefruits.security.enums import Permission
        from ninefruits.security.services.authorization import authorization

        return authorization().scope_for(user, Permission.ADDITIONAL_PROGRAMS_APPROVE).covers(self.org_unit_id, self.pk)
