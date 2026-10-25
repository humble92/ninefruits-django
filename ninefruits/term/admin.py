"""Academic years, term types, terms (with sessions and business windows) and class periods in
the admin panel (original Filament ``Resources/Reference/{AcademicYears,TermTypes,Terms,TimeSlots}``).

The term status changes only with the Change status action (``ChangeTermStatus``), not in the
form. Window times are entered and shown in the institution time zone (admin time zone
middleware) and stored in UTC; class period times are wall-clock times without conversion."""

from __future__ import annotations

from typing import Any, ClassVar

from django import forms
from django.contrib import admin, messages
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import models
from django.db.models import Count
from django.http import HttpRequest, HttpResponse, HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.urls import path, reverse
from django.utils.dates import WEEKDAYS_ABBR
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _
from django.utils.translation import ngettext, pgettext_lazy
from unfold.admin import StackedInline, TabularInline
from unfold.decorators import action, display
from unfold.forms import BaseDialogForm
from unfold.widgets import (
    UnfoldAdminCheckboxSelectMultipleWidget,
    UnfoldAdminSelectWidget,
    UnfoldAdminSplitDateTimeWidget,
    UnfoldAdminTextareaWidget,
)

from ninefruits.adminpanel.mixins import CatalogPermissionMixin
from ninefruits.institution.admin_support import ReferenceAdmin, admin_url, render_action_form, show_errors
from ninefruits.institution.target_criteria_fields import TargetCriteriaForm, criteria_summary
from ninefruits.security.enums import Permission
from ninefruits.term.actions import ChangeTermStatus, CopySessionWindows
from ninefruits.term.enums import TermStatus, TermWindowType
from ninefruits.term.models import AcademicYear, Term, TermSession, TermType, TermWindow, TimeSlot


def _name(obj: Any) -> str:
    return str(obj.name or "")


# -- term types and academic years --------------------------------------------------------------
@admin.register(TermType)
class TermTypeAdmin(ReferenceAdmin):
    manage_permission = Permission.TERMS_MANAGE
    navigation_icon = "sunny"
    navigation_order = 41
    fields = ("code", "name", "is_regular", "sort_order")
    list_display = ("code", "name_column", "is_regular", "sort_order")
    search_fields = ("code",)
    ordering = ("sort_order", "code")

    @display(description=pgettext_lazy("reference", "Name"))
    def name_column(self, obj: TermType) -> str:
        return _name(obj)


class AcademicYearForm(forms.ModelForm):  # type: ignore[type-arg]
    class Meta:
        model = AcademicYear
        fields = ("code", "name", "start_date", "end_date")

    def clean(self) -> dict[str, Any]:
        cleaned = super().clean() or {}
        start, end = cleaned.get("start_date"), cleaned.get("end_date")
        if start and end and end <= start:
            self.add_error(
                "end_date",
                _("The %(attribute)s field must be a date after %(date)s.")
                % {"attribute": _("End date"), "date": _("Start date")},
            )
        return cleaned


@admin.register(AcademicYear)
class AcademicYearAdmin(ReferenceAdmin):
    manage_permission = Permission.TERMS_MANAGE
    navigation_icon = "calendar_month"
    navigation_order = 40
    form = AcademicYearForm
    list_display = ("code", "name_column", "start_date", "end_date")
    search_fields = ("code",)
    ordering = ("start_date",)

    @display(description=pgettext_lazy("reference", "Name"))
    def name_column(self, obj: AcademicYear) -> str:
        return _name(obj)


# -- terms ----------------------------------------------------------------------------------------
class TermForm(forms.ModelForm):  # type: ignore[type-arg]
    class Meta:
        model = Term
        fields = ("academic_year", "term_type", "code", "name", "start_date", "end_date")

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.fields["academic_year"].queryset = AcademicYear.objects.order_by("-start_date")  # type: ignore[attr-defined]
        self.fields["term_type"].queryset = TermType.objects.order_by("sort_order", "code")  # type: ignore[attr-defined]

    def clean(self) -> dict[str, Any]:
        cleaned = super().clean() or {}
        start, end = cleaned.get("start_date"), cleaned.get("end_date")
        if start and end and end < start:
            self.add_error(
                "end_date",
                _("The %(attribute)s field must be a date after or equal to %(date)s.")
                % {"attribute": _("Classes end"), "date": _("Classes start")},
            )
        if self.instance.pk and start and end and not self.errors:
            outside = (
                TermSession.objects.filter(term_id=self.instance.pk, is_full_term=False)
                .filter(models.Q(start_date__lt=start) | models.Q(end_date__gt=end))
                .exists()
            )
            if outside:
                self.add_error("start_date", _("Some sessions would fall outside the new dates. Change them first."))
        return cleaned


class TermSessionForm(forms.ModelForm):  # type: ignore[type-arg]
    term: Term | None = None

    class Meta:
        model = TermSession
        fields = ("code", "sort_order", "name", "start_date", "end_date")

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        if self.instance.pk and self.instance.is_full_term:
            # The full-term session follows the term's code and dates.
            for name in ("code", "start_date", "end_date"):
                self.fields[name].disabled = True

    def clean_code(self) -> str:
        code = str(self.cleaned_data["code"])
        if not self.fields["code"].disabled and not all(char.isalnum() or char in "-_" for char in code):
            raise ValidationError(
                _("The %(attribute)s field must only contain letters, numbers, dashes, and underscores.")
                % {"attribute": "code"}
            )
        return code

    def clean(self) -> dict[str, Any]:
        cleaned = super().clean() or {}
        start, end = cleaned.get("start_date"), cleaned.get("end_date")
        if start and end and end < start:
            self.add_error(
                "end_date",
                _("The %(attribute)s field must be a date after or equal to %(date)s.")
                % {"attribute": _("End date"), "date": _("Start date")},
            )
        term = self.term
        if term is not None and not (self.instance.pk and self.instance.is_full_term):
            for name in ("start_date", "end_date"):
                value = cleaned.get(name)
                if value and not term.start_date <= value <= term.end_date:
                    self.add_error(
                        name,
                        _("The session must lie within its term (%(start)s - %(end)s).")
                        % {"start": term.start_date.isoformat(), "end": term.end_date.isoformat()},
                    )
        return cleaned


class TermSessionFormSet(forms.BaseInlineFormSet):  # type: ignore[type-arg]
    def clean(self) -> None:
        super().clean()
        for form in self.forms:
            if form.instance.pk and form.instance.is_full_term and form.cleaned_data.get("DELETE"):
                raise ValidationError(_("The full-term session belongs to the term and cannot be deleted."))


class TermSessionInline(CatalogPermissionMixin, TabularInline):
    """Sessions of a term. The full-term session is created with the term and follows its
    dates; other sessions (halves, intensive blocks) are added here."""

    model = TermSession
    fk_name = "term"
    form = TermSessionForm
    formset = TermSessionFormSet
    extra = 0
    fields = ("code", "sort_order", "name", "start_date", "end_date", "is_full_term", "windows_count", "copy_link")
    readonly_fields = ("is_full_term", "windows_count", "copy_link")
    verbose_name = _("session")
    verbose_name_plural = _("sessions")
    tab = True
    permissions: ClassVar[dict[str, str]] = {
        "view": Permission.REFERENCE_DATA_VIEW,
        "add": Permission.TERMS_MANAGE,
        "change": Permission.TERMS_MANAGE,
        "delete": Permission.TERMS_MANAGE,
    }

    def has_add_permission(self, request: HttpRequest, obj: Any = None) -> bool:
        return self._allowed(request, "add")

    def get_queryset(self, request: HttpRequest) -> Any:
        return super().get_queryset(request).annotate(window_total=Count("windows"))

    def get_formset(self, request: HttpRequest, obj: Any = None, **kwargs: Any) -> Any:
        self._request = request
        kwargs["form"] = type("TermSessionForm", (self.form,), {"term": obj})
        return super().get_formset(request, obj, **kwargs)

    @display(description=_("term windows"))
    def windows_count(self, obj: TermSession) -> int:
        return int(getattr(obj, "window_total", 0) or 0)

    @admin.display(description="")
    def copy_link(self, obj: TermSession) -> str:
        request = getattr(self, "_request", None)
        if obj.pk is None or obj.is_full_term or request is None or not request.user.has_perm(Permission.TERMS_MANAGE):
            return ""
        url = reverse("admin:term_term_copy_session_windows", args=[obj.term_id, obj.pk])
        return format_html('<a href="{}" class="text-primary-600 underline">{}</a>', url, _("Copy windows"))


class TermWindowForm(TargetCriteriaForm):
    term: Term | None = None

    class Meta:
        model = TermWindow
        fields = ("window_type", "session", "name", "opens_at", "closes_at")
        field_classes = {"opens_at": forms.SplitDateTimeField, "closes_at": forms.SplitDateTimeField}
        widgets = {"opens_at": UnfoldAdminSplitDateTimeWidget, "closes_at": UnfoldAdminSplitDateTimeWidget}

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        term_id = self.term.pk if self.term is not None else self.instance.term_id
        self.fields["session"].queryset = TermSession.objects.filter(term_id=term_id)  # type: ignore[attr-defined]
        self.fields["session"].required = False
        self.fields["session"].empty_label = _("Full term")  # type: ignore[attr-defined]

    def clean(self) -> dict[str, Any]:
        cleaned = super().clean()
        opens, closes = cleaned.get("opens_at"), cleaned.get("closes_at")
        if opens and closes and closes <= opens:
            self.add_error(
                "closes_at",
                _("The %(attribute)s field must be a date after %(date)s.")
                % {"attribute": pgettext_lazy("reference", "Closes"), "date": pgettext_lazy("reference", "Opens")},
            )
        window_type = cleaned.get("window_type")
        if window_type and not TermWindowType(window_type).is_course_scoped():
            cleaned["session"] = None
        return cleaned


class TermWindowInline(CatalogPermissionMixin, StackedInline):
    """Business windows of a term. Several windows of one type with different eligibility make a
    staggered opening (e.g. fourth-year students first). Windows about courses belong to a
    session."""

    model = TermWindow
    fk_name = "term"
    form = TermWindowForm
    extra = 0
    verbose_name = _("term window")
    verbose_name_plural = _("term windows")
    tab = True
    fieldsets = (
        (None, {"fields": ("window_type", "session", "name", "opens_at", "closes_at", "eligibility_display")}),
        (
            _("Eligibility"),
            {
                "classes": ("collapse",),
                "description": _(
                    "Leave empty for everyone. Several windows of the same type with different conditions open in "
                    "stages."
                ),
                "fields": (
                    "eligibility__year_levels",
                    ("eligibility__admission_year_from", "eligibility__admission_year_to"),
                    "eligibility__program_ids",
                    "eligibility__org_unit_ids",
                    "eligibility__academic_standings",
                ),
            },
        ),
    )
    readonly_fields = ("eligibility_display",)
    permissions: ClassVar[dict[str, str]] = {
        "view": Permission.REFERENCE_DATA_VIEW,
        "add": Permission.TERM_WINDOWS_MANAGE,
        "change": Permission.TERM_WINDOWS_MANAGE,
        "delete": Permission.TERM_WINDOWS_MANAGE,
    }

    def has_add_permission(self, request: HttpRequest, obj: Any = None) -> bool:
        return self._allowed(request, "add")

    def get_queryset(self, request: HttpRequest) -> Any:
        return super().get_queryset(request).select_related("session").order_by("opens_at", "id")

    def get_formset(self, request: HttpRequest, obj: Any = None, **kwargs: Any) -> Any:
        kwargs["form"] = type("TermWindowForm", (self.form,), {"term": obj})
        return super().get_formset(request, obj, **kwargs)

    @display(description=_("Eligibility"))
    def eligibility_display(self, obj: TermWindow) -> str:
        if obj.pk is None:
            return "-"
        criteria = obj.eligibility
        return str(_("Everyone")) if criteria.is_everyone() else f"{_('Restricted')}: {criteria_summary(criteria)}"


class ChangeStatusForm(BaseDialogForm):
    status = forms.ChoiceField(label=pgettext_lazy("reference", "Status"), widget=UnfoldAdminSelectWidget)
    reason = forms.CharField(
        label=pgettext_lazy("common", "Reason"),
        max_length=1000,
        required=False,
        widget=UnfoldAdminTextareaWidget(attrs={"rows": 3}),
    )

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        term = Term.objects.filter(pk=self.object_id).first() if self.object_id is not None else None
        allowed = TermStatus(term.status).allowed_next() if term else []
        self.fields["status"].choices = [(status.value, status.label) for status in allowed]  # type: ignore[attr-defined]


class CopyWindowsForm(forms.Form):
    source = forms.ModelChoiceField(
        label=_("Copy from session"), queryset=TermSession.objects.none(), widget=UnfoldAdminSelectWidget
    )

    def __init__(self, *args: Any, target: TermSession, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        sessions = TermSession.objects.filter(term_id=target.term_id).exclude(pk=target.pk)
        self.fields["source"].queryset = sessions  # type: ignore[attr-defined]
        self.fields["source"].initial = sessions.filter(is_full_term=True).values_list("pk", flat=True).first()


class StatusFilter(admin.SimpleListFilter):
    title = pgettext_lazy("reference", "Status")
    parameter_name = "status"

    def lookups(self, request: HttpRequest, model_admin: Any) -> list[tuple[str, Any]]:
        return list(TermStatus.choices)

    def queryset(self, request: HttpRequest, queryset: Any) -> Any:
        return queryset.filter(status=self.value()) if self.value() else queryset


@admin.register(Term)
class TermAdmin(ReferenceAdmin):
    """Terms and their business windows. The status is changed only with the Change status
    action, not in the form."""

    manage_permission = Permission.TERMS_MANAGE
    navigation_icon = "event"
    navigation_order = 42
    form = TermForm
    list_display = (
        "code",
        "name_column",
        "academic_year_column",
        "term_type_column",
        "start_date",
        "end_date",
        "status_column",
        "windows_count",
    )
    list_filter = ("academic_year", StatusFilter)
    list_select_related = ("academic_year", "term_type")
    search_fields = ("code",)
    translated_search_fields = ()
    ordering = ("-start_date",)
    inlines = (TermSessionInline, TermWindowInline)
    actions_detail = ("change_status",)

    def has_delete_permission(self, request: HttpRequest, obj: Any = None) -> bool:
        """Terms are archived, not deleted (the original had no delete)."""
        return False

    def get_queryset(self, request: HttpRequest) -> Any:
        return super().get_queryset(request).annotate(window_total=Count("windows", distinct=True))

    def get_inlines(self, request: HttpRequest, obj: Any) -> Any:
        return self.inlines if obj is not None else ()

    def response_add(self, request: HttpRequest, obj: Term, post_url_continue: str | None = None) -> HttpResponse:
        """To the change page, where sessions and windows are added (original ``CreateTerm``)."""
        if "_addanother" not in request.POST and "_popup" not in request.POST:
            return HttpResponseRedirect(admin_url(obj))
        return super().response_add(request, obj, post_url_continue)

    @display(description=pgettext_lazy("reference", "Name"))
    def name_column(self, obj: Term) -> str:
        return _name(obj)

    @display(description=_("Academic year"))
    def academic_year_column(self, obj: Term) -> str:
        return _name(obj.academic_year)

    @display(description=_("Term type"))
    def term_type_column(self, obj: Term) -> str:
        return _name(obj.term_type)

    @display(description=pgettext_lazy("reference", "Status"), label=True)
    def status_column(self, obj: Term) -> str:
        return str(TermStatus(obj.status).label)

    @display(description=_("Windows"), ordering="window_total")
    def windows_count(self, obj: Term) -> int:
        return int(getattr(obj, "window_total", 0) or 0)

    # -- change status --------------------------------------------------------------------------
    def has_change_status_permission(self, request: HttpRequest, object_id: Any = None) -> bool:
        if not request.user.has_perm(Permission.TERMS_MANAGE):
            return False
        term = Term.objects.filter(pk=object_id).first() if object_id is not None else None
        return term is None or bool(TermStatus(term.status).allowed_next())

    @action(
        description=_("Change status"),
        url_path="change-status",
        permissions=["change_status"],
        icon="sync",
        dialog={"title": _("Change status"), "form_class": ChangeStatusForm},
    )
    def change_status(self, request: HttpRequest, form: ChangeStatusForm, object_id: Any) -> HttpResponse:
        term = get_object_or_404(Term, pk=object_id)
        try:
            ChangeTermStatus()(term, form.cleaned_data["status"], form.cleaned_data.get("reason") or None, request.user)
        except ValidationError as error:
            show_errors(request, error)
        else:
            messages.success(request, _("Term status changed."))
        return HttpResponseRedirect(admin_url(term))

    # -- copy session windows -------------------------------------------------------------------
    def get_urls(self) -> list[Any]:
        return [
            path(
                "<int:term_id>/sessions/<int:session_id>/copy-windows/",
                self.admin_site.admin_view(self.copy_session_windows_view),
                name="term_term_copy_session_windows",
            ),
            *super().get_urls(),
        ]

    def copy_session_windows_view(self, request: HttpRequest, term_id: int, session_id: int) -> HttpResponse:
        target = get_object_or_404(TermSession, pk=session_id, term_id=term_id, is_full_term=False)
        if not request.user.has_perm(Permission.TERMS_MANAGE):
            raise PermissionDenied
        form = CopyWindowsForm(request.POST or None, target=target)
        if request.method == "POST" and form.is_valid():
            try:
                count = CopySessionWindows()(form.cleaned_data["source"], target, request.user)
            except ValidationError as error:
                for message in error.messages:
                    form.add_error(None, message)
            else:
                if count == 0:
                    messages.info(request, _("No windows to copy."))
                else:
                    messages.success(
                        request,
                        ngettext("One window copied.", "%(count)s windows copied.", count) % {"count": count},
                    )
                return HttpResponseRedirect(admin_url(target.term))
        return render_action_form(
            self,
            request,
            form,
            _("Copy windows"),
            admin_url(target.term),
            subtitle=f"{target.term} · {target}",
            description=_(
                "Copies the course windows (add/drop, withdrawal, grading, evaluation) of another session, moved to "
                "this session's dates: early windows keep their distance from the start, late ones from the end. "
                "Adjust them after copying."
            ),
        )


# -- class periods --------------------------------------------------------------------------------
WEEKDAYS = (1, 2, 3, 4, 5, 6, 7)


class TimeSlotForm(forms.ModelForm):  # type: ignore[type-arg]
    weekdays = forms.TypedMultipleChoiceField(
        label=_("Days"), coerce=int, choices=(), widget=UnfoldAdminCheckboxSelectMultipleWidget
    )

    class Meta:
        model = TimeSlot
        fields = ("code", "name", "start_time", "end_time", "weekdays", "sort_order", "is_active")

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        # ISO weekday numbers, 1 = Monday, with the short name in the current language.
        self.fields["weekdays"].choices = [(day, WEEKDAYS_ABBR[day - 1]) for day in WEEKDAYS]  # type: ignore[attr-defined]

    def clean(self) -> dict[str, Any]:
        cleaned = super().clean() or {}
        start, end = cleaned.get("start_time"), cleaned.get("end_time")
        if start and end and end <= start:
            self.add_error(
                "end_time",
                _("The %(attribute)s field must be a date after %(date)s.")
                % {"attribute": _("End"), "date": pgettext_lazy("reference", "Start")},
            )
        return cleaned

    def clean_weekdays(self) -> list[int]:
        return sorted(int(day) for day in self.cleaned_data["weekdays"])


@admin.register(TimeSlot)
class TimeSlotAdmin(ReferenceAdmin):
    manage_permission = Permission.TERMS_MANAGE
    navigation_icon = "schedule"
    navigation_order = 44
    form = TimeSlotForm
    list_display = ("code", "name_column", "start_column", "end_column", "is_active")
    search_fields = ("code",)
    ordering = ("sort_order", "code")

    @display(description=pgettext_lazy("reference", "Name"))
    def name_column(self, obj: TimeSlot) -> str:
        return _name(obj)

    @display(description=pgettext_lazy("reference", "Start"))
    def start_column(self, obj: TimeSlot) -> str:
        return obj.start_time.strftime("%H:%M")

    @display(description=_("End"))
    def end_column(self, obj: TimeSlot) -> str:
        return obj.end_time.strftime("%H:%M")
