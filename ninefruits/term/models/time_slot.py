"""Class period (original ``App\\Models\\Term\\TimeSlot``, legacy TTTIME), e.g. period 1 from
09:00 to 09:50 on weekdays. Times are wall-clock times without a time zone."""

from __future__ import annotations

from django.db import models
from django.utils.translation import gettext_lazy as _
from django.utils.translation import pgettext_lazy

from ninefruits.core.models import TimeStampedModel, VisibleQuerySet
from ninefruits.i18n.fields import TranslatableJSONField


class TimeSlot(TimeStampedModel):
    code = models.CharField(pgettext_lazy("reference", "Code"), max_length=32, unique=True)
    name = TranslatableJSONField(pgettext_lazy("reference", "Name"))
    start_time = models.TimeField(pgettext_lazy("reference", "Start"))
    end_time = models.TimeField(_("End"))
    #: ISO-8601 weekday numbers, 1 = Monday.
    weekdays = models.JSONField(_("Days"), default=list)
    sort_order = models.IntegerField(_("Order"), default=0)
    is_active = models.BooleanField(pgettext_lazy("reference.fields", "Active"), default=True)

    objects = VisibleQuerySet.as_manager()

    class Meta:
        db_table = "time_slots"
        ordering = ["sort_order", "code"]
        verbose_name = _("class period")
        verbose_name_plural = _("class periods")

    def __str__(self) -> str:
        return str(self.name or self.code)
