"""Shared pieces of the person admin screens."""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from django import forms
from django.contrib import messages
from django.core.exceptions import ValidationError
from django.http import HttpRequest, HttpResponse
from django.urls import reverse
from django.utils.translation import pgettext_lazy
from unfold.widgets import UnfoldAdminSelectWidget, UnfoldAdminTextareaWidget

from ninefruits.institution.admin_support import render_action_form

REASON_LABEL = pgettext_lazy("common", "Reason")


def reason_field(max_length: int = 1000) -> forms.CharField:
    return forms.CharField(
        label=REASON_LABEL, max_length=max_length, widget=UnfoldAdminTextareaWidget(attrs={"rows": 3})
    )


def note_field(required: bool) -> forms.CharField:
    return forms.CharField(
        label=pgettext_lazy("people", "Decision note"),
        required=required,
        max_length=1000,
        widget=UnfoldAdminTextareaWidget(attrs={"rows": 3}),
    )


def select(choices: Iterable[tuple[Any, Any]] = ()) -> UnfoldAdminSelectWidget:
    widget = UnfoldAdminSelectWidget()
    widget.choices = list(choices)
    return widget


def admin_change_url(obj: Any) -> str:
    opts = obj._meta
    return reverse(f"admin:{opts.app_label}_{opts.model_name}_change", args=[obj.pk])


def apply_errors(form: forms.Form, error: ValidationError) -> None:
    """Domain errors on the form (field when the form has it, else the whole form)."""
    if hasattr(error, "error_dict"):
        for field, errors in error.message_dict.items():
            form.add_error(field if field in form.fields else None, errors)
    else:
        form.add_error(None, error.messages)


def show_errors(request: HttpRequest, error: ValidationError) -> None:
    for message in error.messages:
        messages.error(request, message)


def form_page(
    model_admin: Any, request: HttpRequest, form: forms.Form, title: Any, back_url: str, **extra: Any
) -> HttpResponse:
    return render_action_form(model_admin, request, form, title, back_url, **extra)


def record_changes(tables_and_ids: Iterable[tuple[str, Iterable[Any]]], limit: int = 50) -> list[Any]:
    """Latest data audit entries (``audit.record_changes``) of the given rows, for the change
    history section of a detail page."""
    from django.db.models import Q

    from ninefruits.audit.models import RecordChange

    condition = Q(pk__in=[])
    for table, ids in tables_and_ids:
        ids = [str(pk) for pk in ids]
        if ids:
            condition |= Q(table_schema="public", table_name=table, record_id__in=ids)
    return list(RecordChange.objects.filter(condition).order_by("-occurred_at", "-id")[:limit])
