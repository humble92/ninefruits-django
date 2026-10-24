"""Code lists (original ``App\\Models\\Institution\\LookupType`` and ``LookupValue``): institution
specific codes such as ethnicity, admission type or room type (legacy FNATION, FADMDIST,
ROOM.FORWHAT ...). System lists are used by the application; their codes cannot change and they
cannot be deleted."""

from __future__ import annotations

from typing import Self

from django.db import models
from django.utils.translation import gettext_lazy as _
from django.utils.translation import pgettext_lazy

from ninefruits.core.models import TimeStampedModel, VisibleQuerySet
from ninefruits.i18n.fields import TranslatableJSONField


class LookupType(TimeStampedModel):
    code = models.CharField(pgettext_lazy("reference", "Code"), max_length=64, unique=True)
    name = TranslatableJSONField(pgettext_lazy("reference", "Name"))
    description = TranslatableJSONField(pgettext_lazy("reference", "Description"), null=True, blank=True)
    is_system = models.BooleanField(_("System"), default=False)

    objects = VisibleQuerySet.as_manager()

    class Meta:
        db_table = "lookup_types"
        ordering = ["code"]
        verbose_name = _("code list")
        verbose_name_plural = _("code lists")

    def __str__(self) -> str:
        return str(self.name or self.code)


class LookupValueQuerySet(VisibleQuerySet):
    def of_type(self, type_code: str) -> Self:
        """Values of the code list with this code (original ``scopeOfType``)."""
        return self.filter(lookup_type__code=type_code)


class LookupValue(TimeStampedModel):
    lookup_type = models.ForeignKey(LookupType, on_delete=models.CASCADE, related_name="values")
    code = models.CharField(pgettext_lazy("reference", "Code"), max_length=64)
    name = TranslatableJSONField(pgettext_lazy("reference", "Name"))
    sort_order = models.IntegerField(_("Order"), default=0)
    is_active = models.BooleanField(pgettext_lazy("reference.fields", "Active"), default=True)

    objects = LookupValueQuerySet.as_manager()

    class Meta:
        db_table = "lookup_values"
        ordering = ["sort_order", "code"]
        verbose_name = _("code")
        verbose_name_plural = _("codes")
        constraints = [
            models.UniqueConstraint(fields=["lookup_type", "code"], name="lookup_values_lookup_type_id_code_unique"),
        ]

    def __str__(self) -> str:
        return str(self.name or self.code)
