"""Shared pieces of the grading admin screens (dialog forms of the original Filament actions,
filters). The registration screens' helpers (``run_form``, term filters) are reused."""

from __future__ import annotations

from typing import Any

from django import forms
from django.contrib import admin
from django.http import HttpRequest
from django.utils.translation import gettext_lazy as _
from django.utils.translation import pgettext_lazy
from unfold.widgets import UnfoldAdminSelectWidget, UnfoldAdminTextareaWidget, UnfoldBooleanSwitchWidget

from ninefruits.registration.admin.common import (
    REASON_MAX,
    ChoiceFilter,
    ConfirmForm,
    DefaultTermFilter,
    ReasonForm,
    reason_field,
    run_form,
    term_choices,
)

__all__ = [
    "REASON_MAX",
    "ChoiceFilter",
    "CloseTermForm",
    "ConfirmForm",
    "DecisionForm",
    "DefaultTermFilter",
    "ReasonForm",
    "RecalculateForm",
    "RequiredDecisionForm",
    "YesNoFilter",
    "run_form",
]


class DecisionForm(forms.Form):
    """Approve: an optional note."""

    note = forms.CharField(
        label=pgettext_lazy("grading", "Note"),
        max_length=REASON_MAX,
        required=False,
        widget=UnfoldAdminTextareaWidget(attrs={"rows": 3}),
    )


class RequiredDecisionForm(DecisionForm):
    """Reject: the note is required."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.fields["note"].required = True


class CloseTermForm(forms.Form):
    term_id = forms.TypedChoiceField(label=_("term"), coerce=int, widget=UnfoldAdminSelectWidget)
    dry_run = forms.BooleanField(
        label=_("Preview only"),
        required=False,
        initial=True,
        widget=UnfoldBooleanSwitchWidget,
        help_text=_("Only check whether the term can close."),
    )
    reason = forms.CharField(
        label=pgettext_lazy("common", "Reason"),
        max_length=REASON_MAX,
        required=False,
        widget=UnfoldAdminTextareaWidget(attrs={"rows": 3}),
    )

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.fields["term_id"].choices = term_choices(("published",))  # type: ignore[attr-defined]


class RecalculateForm(forms.Form):
    term_id = forms.TypedChoiceField(label=_("term"), coerce=int, widget=UnfoldAdminSelectWidget)
    reason = reason_field()

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.fields["term_id"].choices = term_choices()  # type: ignore[attr-defined]


class YesNoFilter(admin.SimpleListFilter):
    """A ternary filter (original ``TernaryFilter``): yes, no or all (default)."""

    def lookups(self, request: HttpRequest, model_admin: Any) -> list[tuple[Any, Any]]:
        return [("yes", _("Yes")), ("no", _("No"))]

    def queryset(self, request: HttpRequest, queryset: Any) -> Any:
        if self.value() == "yes":
            return self.when_yes(queryset)
        if self.value() == "no":
            return self.when_no(queryset)
        return queryset

    def when_yes(self, queryset: Any) -> Any:
        raise NotImplementedError

    def when_no(self, queryset: Any) -> Any:
        raise NotImplementedError
