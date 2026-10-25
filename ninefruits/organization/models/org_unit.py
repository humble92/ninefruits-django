"""Org units (original ``App\\Models\\Organization\\OrgUnitType``, ``OrgUnit`` and
``OrgUnitSuccession``, ADR 0006).

A unit (university, college, department, major or office) is valid for a period. A
reorganization ends the unit and links successors (``OrgUnitSuccession``) instead of editing
history. ``parent`` builds the hierarchy; the database trigger
``org_units_before_write_prevent_cycle`` refuses placing a unit under itself or a descendant."""

from __future__ import annotations

from collections.abc import Iterable

from django.db import connection, models
from django.utils.translation import gettext_lazy as _
from django.utils.translation import pgettext_lazy

from ninefruits.core.models import EffectivePeriodMixin, EffectiveQuerySet, TimeStampedModel, VisibleQuerySet
from ninefruits.i18n.fields import TranslatableJSONField
from ninefruits.organization.enums import OrgUnitChangeType


class OrgUnitType(TimeStampedModel):
    """E.g. university, college, department, major, administrative office."""

    code = models.CharField(pgettext_lazy("reference", "Code"), max_length=64, unique=True)
    name = TranslatableJSONField(pgettext_lazy("reference", "Name"))
    is_academic = models.BooleanField(pgettext_lazy("reference", "Academic"), default=True)
    sort_order = models.IntegerField(_("Order"), default=0)

    objects = VisibleQuerySet.as_manager()

    class Meta:
        db_table = "org_unit_types"
        ordering = ["sort_order", "code"]
        verbose_name = _("org unit type")
        verbose_name_plural = _("org unit types")

    def __str__(self) -> str:
        return str(self.name or self.code)


class OrgUnitQuerySet(EffectiveQuerySet):
    pass


class OrgUnit(EffectivePeriodMixin, TimeStampedModel):
    code = models.CharField(pgettext_lazy("reference", "Code"), max_length=64, unique=True)
    name = TranslatableJSONField(pgettext_lazy("reference", "Name"))
    short_name = TranslatableJSONField(_("Short name"), null=True, blank=True)
    org_unit_type = models.ForeignKey(
        OrgUnitType, on_delete=models.RESTRICT, related_name="org_units", verbose_name=_("Type")
    )
    parent = models.ForeignKey(
        "self", on_delete=models.RESTRICT, null=True, blank=True, related_name="children", verbose_name=_("Parent")
    )
    sort_order = models.IntegerField(_("Order"), default=0)

    objects = OrgUnitQuerySet.as_manager()

    class Meta:
        db_table = "org_units"
        ordering = ["code"]
        verbose_name = _("org unit")
        verbose_name_plural = _("org units")

    def __str__(self) -> str:
        return f"{self.code} {self.name or ''}".strip()

    @property
    def type(self) -> OrgUnitType:
        return self.org_unit_type

    @staticmethod
    def descendant_ids_of(ids: Iterable[int]) -> list[int]:
        """The units and every unit below them (``util.org_unit_descendant_ids``)."""
        from ninefruits.security.services.authorization import org_unit_descendant_ids

        roots = [int(pk) for pk in ids]
        return org_unit_descendant_ids(roots) if roots else []

    def ancestor_ids(self) -> list[int]:
        """Ids from this unit up to the root, nearest first (``util.org_unit_ancestor_ids``)."""
        with connection.cursor() as cursor:
            cursor.execute("SELECT util.org_unit_ancestor_ids(%s)", [self.pk])
            row = cursor.fetchone()
        return [int(pk) for pk in (row[0] or [])] if row else []


class OrgUnitSuccession(TimeStampedModel):
    """A unit that took over from another after a reorganization."""

    predecessor = models.ForeignKey(
        OrgUnit,
        on_delete=models.CASCADE,
        related_name="successions",
        db_column="predecessor_org_unit_id",
    )
    successor = models.ForeignKey(
        OrgUnit,
        on_delete=models.CASCADE,
        related_name="predecessions",
        db_column="successor_org_unit_id",
        verbose_name=_("Successor"),
    )
    change_type = models.CharField(
        pgettext_lazy("reference", "Change"), max_length=32, choices=OrgUnitChangeType.choices
    )
    effective_date = models.DateField(pgettext_lazy("reference", "Effective date"))
    reason = models.TextField(pgettext_lazy("common", "Reason"), null=True, blank=True)

    objects = VisibleQuerySet.as_manager()

    class Meta:
        db_table = "org_unit_successions"
        ordering = ["effective_date", "id"]
        verbose_name = _("successor")
        verbose_name_plural = _("successors")

    def __str__(self) -> str:
        return f"{self.predecessor_id} -> {self.successor_id}"
