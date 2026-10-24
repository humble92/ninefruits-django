"""Buildings and rooms (original ``App\\Models\\Facility\\Building`` and ``Room``). The room type
is a value of the ``room_type`` code list."""

from __future__ import annotations

from django.db import models
from django.utils.translation import gettext_lazy as _
from django.utils.translation import pgettext_lazy

from ninefruits.core.models import TimeStampedModel, VisibleQuerySet
from ninefruits.i18n.fields import TranslatableJSONField
from ninefruits.institution.models import LookupValue
from ninefruits.organization.models import OrgUnit


class Building(TimeStampedModel):
    code = models.CharField(pgettext_lazy("reference", "Code"), max_length=32, unique=True)
    name = TranslatableJSONField(pgettext_lazy("reference", "Name"))
    address = models.TextField(_("Address"), null=True, blank=True)
    is_active = models.BooleanField(pgettext_lazy("reference.fields", "Active"), default=True)

    objects = VisibleQuerySet.as_manager()

    class Meta:
        db_table = "buildings"
        ordering = ["code"]
        verbose_name = _("building")
        verbose_name_plural = _("buildings")

    def __str__(self) -> str:
        return f"{self.code} {self.name or ''}".strip()


class Room(TimeStampedModel):
    #: Code of the code list holding room types.
    ROOM_TYPE_LOOKUP = "room_type"

    building = models.ForeignKey(Building, on_delete=models.RESTRICT, related_name="rooms", verbose_name=_("Building"))
    code = models.CharField(_("Room number"), max_length=32)
    name = TranslatableJSONField(pgettext_lazy("reference", "Name"), null=True, blank=True)
    room_type = models.ForeignKey(
        LookupValue,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
        verbose_name=_("Room type"),
    )
    org_unit = models.ForeignKey(
        OrgUnit, on_delete=models.SET_NULL, null=True, blank=True, related_name="rooms", verbose_name=_("Org unit")
    )
    capacity = models.IntegerField(pgettext_lazy("reference", "Capacity"), null=True, blank=True)
    is_schedulable = models.BooleanField(
        _("Used for timetables"), default=True, help_text=_("Offered when timetables are made.")
    )
    is_active = models.BooleanField(pgettext_lazy("reference.fields", "Active"), default=True)
    note = models.TextField(pgettext_lazy("reference", "Note"), null=True, blank=True)

    objects = VisibleQuerySet.as_manager()

    class Meta:
        db_table = "rooms"
        ordering = ["building__code", "code"]
        verbose_name = _("room")
        verbose_name_plural = _("rooms")
        constraints = [
            models.UniqueConstraint(fields=["building", "code"], name="rooms_building_id_code_unique"),
        ]

    def __str__(self) -> str:
        return self.label()

    def label(self) -> str:
        """Display label such as "Science Hall 101"."""
        return f"{self.building.name} {self.code}".strip()
