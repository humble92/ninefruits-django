from __future__ import annotations

from typing import Any, cast

from django import forms
from django.contrib import admin, messages
from django.core.exceptions import PermissionDenied, ValidationError
from django.core.paginator import Paginator
from django.http import HttpRequest, HttpResponse, QueryDict
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.utils.http import urlencode
from django.utils.translation import gettext_lazy as _
from unfold.widgets import UnfoldAdminDateWidget, UnfoldAdminSelectWidget, UnfoldAdminTextInputWidget

from ninefruits.adminpanel.navigation import NavigationGroup
from ninefruits.i18n.formatting import institution_timezone
from ninefruits.organization.models import Program
from ninefruits.person.actions.year_levels import ManageYearLevels
from ninefruits.person.models import YearLevelRule, YearLevelRun
from ninefruits.security.enums import Permission
from ninefruits.security.models import User
from ninefruits.term.models import Term

BASES = {"credits": _("Earned credits"), "terms": _("Completed terms"), "manual": _("Manual only")}
STATUSES = {"draft": _("Draft"), "scheduled": _("Scheduled"), "applied": _("Applied"), "canceled": _("Canceled")}
OUTCOMES = {
    None: _("Pending"),
    "applied": _("Updated"),
    "stale": _("Record changed after preview"),
    "excluded": _("Excluded"),
}


class RuleForm(forms.ModelForm):  # type: ignore[type-arg]
    basis = forms.ChoiceField(label=_("Calculation basis"), choices=list(BASES.items()), widget=UnfoldAdminSelectWidget)
    minimums = forms.CharField(
        label=_("Promotion thresholds"),
        required=False,
        widget=UnfoldAdminTextInputWidget,
        help_text=_("Enter comma-separated minimum totals in ascending order, starting with year 2."),
        max_length=150,
    )

    class Meta:
        model = YearLevelRule
        fields = ("name", "basis", "minimums", "is_default")
        labels = {"is_default": _("Institution default")}

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        if self.instance.pk:
            self.initial["minimums"] = ", ".join(str(row["minimum"]) for row in self.instance.thresholds)


class PreviewForm(forms.Form):
    term = forms.ModelChoiceField(
        label=_("Target term"), queryset=Term.objects.order_by("-start_date"), widget=UnfoldAdminSelectWidget
    )
    program = forms.ModelChoiceField(
        label=_("Program"),
        queryset=Program.objects.order_by("code"),
        required=False,
        empty_label=_("All programs"),
        widget=UnfoldAdminSelectWidget,
    )
    cutoff_date = forms.DateField(label=_("Results through"), widget=UnfoldAdminDateWidget)


class ReviewFilter(forms.Form):
    program = forms.ModelChoiceField(
        label=_("Program filter (display only)"),
        queryset=Program.objects.none(),
        required=False,
        empty_label=_("All programs"),
        widget=UnfoldAdminSelectWidget,
    )

    def __init__(self, data: QueryDict, run: YearLevelRun) -> None:
        super().__init__(data)
        field = self.fields["program"]
        assert isinstance(field, forms.ModelChoiceField)
        field.queryset = Program.objects.filter(pk__in=run.changes.values("program_id")).order_by("code")


class ScheduleForm(forms.Form):
    scheduled_at = forms.DateTimeField(
        label=_("Apply at"),
        widget=UnfoldAdminTextInputWidget(attrs={"type": "datetime-local"}),
    )


def _pk(data: QueryDict, key: str) -> int | None:
    value = data.get(key, "")
    return int(value) if value.isascii() and value.isdecimal() and len(value) < 19 else None


def rules_view(request: HttpRequest) -> HttpResponse:
    actions = ManageYearLevels()
    staff = cast(User, request.user)
    if not actions.can_configure(staff):
        raise PermissionDenied
    rule_id = _pk(request.GET, "rule")
    rule = get_object_or_404(YearLevelRule, pk=rule_id) if rule_id else YearLevelRule()
    form = RuleForm(request.POST if request.method == "POST" else None, instance=rule)
    if request.method == "POST" and form.is_valid():
        data = form.cleaned_data
        try:
            actions.save_rule(
                rule,
                {
                    **data,
                    "thresholds": [{"minimum": value.strip()} for value in data["minimums"].split(",")],
                },
                staff,
            )
        except ValidationError as exc:
            form.add_error(None, exc)
        else:
            return redirect("admin:year_level_rules")
    return render(
        request,
        "person/admin/year_level_rules.html",
        {
            **admin.site.each_context(request),
            "title": _("Year-level rules"),
            "form": form,
            "rules": [(item, BASES[item.basis]) for item in YearLevelRule.objects.order_by("pk")],
        },
    )


def progression_view(request: HttpRequest) -> HttpResponse:
    actions = ManageYearLevels()
    staff = cast(User, request.user)
    if not actions.can_manage(staff):
        raise PermissionDenied
    run_id = _pk(request.GET, "run")
    run = get_object_or_404(YearLevelRun.objects.select_related("term", "program"), pk=run_id) if run_id else None
    institution_zone = institution_timezone()
    with timezone.override(institution_zone):
        return _progression_response(request, actions, staff, run, str(institution_zone))


def _progression_response(
    request: HttpRequest,
    actions: ManageYearLevels,
    staff: User,
    run: YearLevelRun | None,
    zone: str,
) -> HttpResponse:
    bound = request.POST if request.method == "POST" else None
    form: forms.Form = (
        PreviewForm(bound) if run is None else ScheduleForm(bound if request.POST.get("action") == "schedule" else None)
    )
    url = reverse("admin:year_level_progression")
    if bound is not None:
        action = bound.get("action")
        try:
            if run is None and action == "preview" and form.is_valid():
                program = form.cleaned_data["program"]
                created = actions.preview(
                    form.cleaned_data["term"].pk,
                    form.cleaned_data["cutoff_date"],
                    staff,
                    program_id=program.pk if program else None,
                )
                return redirect(f"{url}?run={created.pk}")
            if run is not None:
                if action == "schedule" and form.is_valid():
                    actions.schedule(run.pk, form.cleaned_data["scheduled_at"], staff)
                    return redirect(f"{url}?run={run.pk}")
                if action == "cancel":
                    actions.cancel(run.pk, staff)
                    return redirect(f"{url}?run={run.pk}")
                if action == "exclude":
                    change_id = _pk(bound, "change")
                    get_object_or_404(run.changes, pk=change_id)
                    actions.exclude(run.pk, cast(int, change_id), staff)
                    params = {"run": run.pk, "page": _pk(request.GET, "page") or 1}
                    if program_id := _pk(request.GET, "program"):
                        params["program"] = program_id
                    return redirect(f"{url}?{urlencode(params)}")
        except ValidationError as exc:
            messages.error(request, " ".join(exc.messages))
    page = _pk(request.GET, "page") or 1
    paginated: dict[str, object]
    if run is None:
        run_page = Paginator(YearLevelRun.objects.select_related("term", "program").order_by("-pk"), 25).get_page(page)
        paginated = {"items": run_page, "run_rows": [(item, STATUSES[item.status]) for item in run_page]}
    else:
        changes = run.changes.select_related("student_record", "program").order_by("pk")
        review_filter = ReviewFilter(request.GET, run) if run.program_id is None else None
        if review_filter and review_filter.is_valid() and (program := review_filter.cleaned_data["program"]):
            changes = changes.filter(program=program)
        change_page = Paginator(changes, 50).get_page(page)
        paginated = {
            "items": change_page,
            "review_filter": review_filter,
            "change_rows": [(item, BASES[item.basis], OUTCOMES[item.outcome]) for item in change_page],
        }
    return render(
        request,
        "person/admin/year_level_progression.html",
        {
            **admin.site.each_context(request),
            "title": _("Year-level progression"),
            "run": run,
            "zone": zone,
            "form": form,
            "run_status": STATUSES[run.status] if run else "",
            **paginated,
        },
    )


admin.site.register_view(  # type: ignore[attr-defined]
    "settings/year-level-rules/",
    rules_view,
    name="year_level_rules",
    permission=Permission.INSTITUTION_SETTINGS_MANAGE,
    navigation_group=NavigationGroup.SETTINGS,
    label=_("Year-level rules"),
)
admin.site.register_view(  # type: ignore[attr-defined]
    "year-level-progression/",
    progression_view,
    name="year_level_progression",
    permission=Permission.STUDENT_RECORDS_MANAGE,
    navigation_group=NavigationGroup.STUDENT_RECORDS,
    label=_("Year-level progression"),
)
