"""The standard reports (original Filament page ``Reports``; legacy report.php menu, many entries
of which were dead): pick a report and its filters, see the first 500 rows, download the CSV.
Only the filters the chosen report takes are shown (original ``visible($uses(...))``); after
changing the report, "Show" brings up its filters. A report with a term filter shows nothing until
a term is chosen."""

from __future__ import annotations

from typing import Any

from django import forms
from django.contrib import admin
from django.http import HttpRequest, HttpResponse, QueryDict
from django.shortcuts import render
from django.urls import reverse
from django.utils.http import urlencode
from django.utils.translation import gettext_lazy as _
from django.utils.translation import pgettext_lazy
from unfold.widgets import UnfoldAdminDateWidget, UnfoldAdminSelectWidget

from ninefruits.grading.enums import AcademicStanding
from ninefruits.person.enums import StudentStatus
from ninefruits.reporting.services import REPORTS, ReportCatalog
from ninefruits.reporting.services.catalog import SCREEN_LIMIT, cell

EMPTY = [("", "---------")]


class ReportForm(forms.Form):
    report = forms.ChoiceField(label=_("Report"), widget=UnfoldAdminSelectWidget)
    term = forms.TypedChoiceField(
        label=_("term"), coerce=int, required=False, empty_value=None, widget=UnfoldAdminSelectWidget
    )
    org_unit = forms.TypedChoiceField(
        label=_("org unit"), coerce=int, required=False, empty_value=None, widget=UnfoldAdminSelectWidget
    )
    status = forms.ChoiceField(
        label=pgettext_lazy("registration", "Status"), required=False, widget=UnfoldAdminSelectWidget
    )
    year_level = forms.TypedChoiceField(
        label=pgettext_lazy("people", "Year"),
        coerce=int,
        required=False,
        empty_value=None,
        choices=[*EMPTY, *((level, str(level)) for level in range(1, 7))],
        widget=UnfoldAdminSelectWidget,
    )
    standing = forms.ChoiceField(label=_("Academic standing"), required=False, widget=UnfoldAdminSelectWidget)
    satisfied = forms.ChoiceField(label=_("Satisfied"), required=False, widget=UnfoldAdminSelectWidget)
    date_from = forms.DateField(label=_("Start date"), required=False, widget=UnfoldAdminDateWidget)
    date_to = forms.DateField(label=_("End date"), required=False, widget=UnfoldAdminDateWidget)

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        from ninefruits.organization.models import OrgUnit
        from ninefruits.registration.admin.common import term_choices

        super().__init__(*args, **kwargs)
        self.fields["report"].choices = [(key, ReportCatalog.name(key)) for key in REPORTS]  # type: ignore[attr-defined]
        self.fields["term"].choices = EMPTY + term_choices()  # type: ignore[attr-defined]
        self.fields["org_unit"].choices = EMPTY + [  # type: ignore[attr-defined]
            (unit.pk, f"{unit.code} {unit.name}") for unit in OrgUnit.objects.order_by("code")
        ]
        self.fields["status"].choices = EMPTY + list(StudentStatus.choices)  # type: ignore[attr-defined]
        self.fields["standing"].choices = EMPTY + list(AcademicStanding.choices)  # type: ignore[attr-defined]
        self.fields["satisfied"].choices = [*EMPTY, ("yes", _("Satisfied")), ("no", _("Not satisfied"))]  # type: ignore[attr-defined]


def chosen_report(data: QueryDict) -> str:
    key = data.get("report") or "students"
    return key if key in REPORTS else "students"


def reports_view(request: HttpRequest) -> HttpResponse:
    data = request.GET.copy()
    key = chosen_report(data)
    data["report"] = key
    definition = REPORTS[key]
    form = ReportForm(data)
    form.is_valid()
    params = {name: str(form.data.get(name)) for name in definition.params if form.data.get(name) not in (None, "")}
    if "term" in definition.params and not params.get("term"):
        rows: list[dict[str, Any]] = []
    else:
        rows = ReportCatalog().rows(key, params, SCREEN_LIMIT)
    columns = [(column, ReportCatalog.column_label(column)) for column in definition.columns]
    table = [[cell(row.get(column)) for column, _label in columns] for row in rows]
    csv_url = reverse("reporting:csv", args=[key]) + ("?" + urlencode(params) if params else "")
    context = {
        **admin.site.each_context(request),
        "title": _("Reports"),
        "form": form,
        "fields": [form["report"], *(form[name] for name in definition.params)],
        "columns": columns,
        "rows": table,
        "row_count": len(table),
        "csv_url": csv_url,
    }
    return render(request, "reporting/admin/reports.html", context)
