"""Model bases shared by the domain apps (porting-plan 9)."""

from __future__ import annotations

from datetime import date
from typing import Any, Self

from django.db import models
from django.utils import timezone


class TimeStampedModel(models.Model):
    """``created_at``/``updated_at`` as in the original (nullable ``timestamptz(0)``)."""

    created_at = models.DateTimeField(null=True, blank=True, default=timezone.now, editable=False)
    updated_at = models.DateTimeField(null=True, blank=True, auto_now=True, editable=False)

    class Meta:
        abstract = True


class VisibleQuerySet(models.QuerySet[Any]):
    """Every model's manager offers ``visible_to(user)``: the rows the user may see according to
    the application scope (RLS gives the same answer in the database). Admin ``get_queryset``,
    portal views and API viewsets must go through it. Models without scoped data return all."""

    def visible_to(self, user: Any) -> Self:
        return self


class EffectiveQuerySet(VisibleQuerySet):
    def effective_on(self, on: date | None = None) -> Self:
        on = on or timezone.localdate()
        return self.filter(effective_start_date__lte=on).filter(
            models.Q(effective_end_date__isnull=True) | models.Q(effective_end_date__gte=on)
        )


class EffectivePeriodMixin(models.Model):
    """Original ``HasEffectivePeriod``: ``effective_start_date``/``effective_end_date`` and the
    generated ``effective_period`` daterange (created by db/schema, read only here)."""

    effective_start_date = models.DateField()
    effective_end_date = models.DateField(null=True, blank=True)

    class Meta:
        abstract = True

    def is_effective_on(self, on: date | None = None) -> bool:
        on = on or timezone.localdate()
        return self.effective_start_date <= on and (self.effective_end_date is None or self.effective_end_date >= on)
