"""Reporting view reads (porting-plan 12: the same scope as the ``app_reporting`` role, i.e. the
eight ``reporting`` views and nothing else).

- ``GET /api/v1/reports/``: the views and their columns;
- ``GET /api/v1/reports/<view>/``: rows, paginated (``?limit=``, ``?offset=``), filtered by exact
  column values (``?term_code=2026-FA&status=enrolled``).

Needs ``reports.view``. The rows are what the user may see: the views are ``security_invoker``,
so row level security applies to the user (session or token), and ``visible_to`` gives the same
answer in the application. Translated columns follow the request language (``Accept-Language``).
Each read is a bulk export of personal data and is recorded as the security event
``data.exported`` with the view, the filters and the row count (porting-plan 11)."""

from __future__ import annotations

from typing import Any

from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import models
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import viewsets
from rest_framework.exceptions import NotFound, ValidationError
from rest_framework.request import Request
from rest_framework.response import Response

from ninefruits.api.pagination import LimitOffsetPagination
from ninefruits.api.permissions import HasCatalogPermission
from ninefruits.audit.security_events import SecurityEventType, record_security_event
from ninefruits.security.enums import Permission

PAGING = {"limit", "offset", "format"}
#: Ordering of the views whose primary key is not unique.
ORDERING: dict[str, tuple[str, ...]] = {"headcount": ("org_unit_id", "program_id", "year_level", "status")}


def view_models() -> dict[str, type[models.Model]]:
    from ninefruits.reporting.models import VIEW_MODELS

    return dict(VIEW_MODELS)


def columns(model: type[models.Model]) -> list[str]:
    """The view's column names (foreign keys by their column, e.g. ``person_id``)."""
    return [str(field.column) for field in model._meta.concrete_fields]


def _attnames(model: type[models.Model]) -> dict[str, str]:
    return {str(field.column): field.attname for field in model._meta.concrete_fields}


def _filterable(model: type[models.Model]) -> dict[str, str]:
    return {
        field.column: field.attname for field in model._meta.concrete_fields if not isinstance(field, models.JSONField)
    }


class ReportViewSet(viewsets.ViewSet):
    permission_classes = [HasCatalogPermission(Permission.REPORTS_VIEW)]
    lookup_field = "name"
    lookup_value_regex = r"[a-z_]+"

    @extend_schema(operation_id="reports_list", responses=OpenApiTypes.OBJECT)
    def list(self, request: Request) -> Response:
        return Response({"views": [{"name": name, "columns": columns(model)} for name, model in view_models().items()]})

    @extend_schema(
        responses=OpenApiTypes.OBJECT,
        parameters=[
            OpenApiParameter("limit", int, description="Rows per page (default 100, at most 1000)"),
            OpenApiParameter("offset", int),
        ],
    )
    def retrieve(self, request: Request, name: str | None = None) -> Response:
        model = view_models().get(str(name))
        if model is None:
            raise NotFound
        attnames = _attnames(model)
        filterable = _filterable(model)
        filters: dict[str, str] = {}
        for column, value in request.query_params.items():
            if column in PAGING:
                continue
            if column not in filterable:
                raise ValidationError({column: "Unknown or unfilterable column."})
            filters[column] = str(value)
        queryset = model._default_manager.visible_to(request.user)  # type: ignore[attr-defined]
        try:
            if filters:
                queryset = queryset.filter(**{filterable[column]: value for column, value in filters.items()})
            ordering = ORDERING.get(str(name), (model._meta.pk.attname,))
            rows = queryset.order_by(*ordering).values(*attnames.values())
            paginator = LimitOffsetPagination()
            page: list[Any] = paginator.paginate_queryset(rows, request, view=self) or []
        except (DjangoValidationError, ValueError, TypeError) as error:
            raise ValidationError({"detail": "A filter value does not fit its column."}) from error
        data = [{column: row[attname] for column, attname in attnames.items()} for row in page]
        record_security_event(
            SecurityEventType.DATA_EXPORTED,
            user=request.user,
            properties={
                "source": "api",
                "view": str(name),
                "filters": filters,
                "rows": len(data),
                "offset": paginator.offset,
            },
        )
        return paginator.get_paginated_response(data)
