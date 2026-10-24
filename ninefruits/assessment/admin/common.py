"""Shared pieces of the examination admin screens."""

from __future__ import annotations

from typing import Any

from django.contrib import admin
from django.http import HttpRequest
from django.utils.translation import pgettext_lazy

from ninefruits.assessment.models import AssessmentType


class TypeFilter(admin.SimpleListFilter):
    """By kind (original ``SelectFilter::make('assessment_type_id')``)."""

    title = pgettext_lazy("assessment", "Kind")
    parameter_name = "type"

    def lookups(self, request: HttpRequest, model_admin: Any) -> list[tuple[Any, Any]]:
        return [(str(kind.pk), str(kind.name)) for kind in AssessmentType.objects.order_by("sort_order", "code")]

    def queryset(self, request: HttpRequest, queryset: Any) -> Any:
        return queryset.filter(assessment_type_id=self.value()) if self.value() else queryset
