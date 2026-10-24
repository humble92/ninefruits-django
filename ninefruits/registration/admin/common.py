"""Shared pieces of the registration admin screens: student and section inputs, term choices,
dialog forms (original Filament action schemas), filters and the "do an action on a row" view."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from django import forms
from django.contrib import admin, messages
from django.core.exceptions import PermissionDenied, ValidationError
from django.http import HttpRequest, HttpResponse, HttpResponseRedirect
from django.utils.http import url_has_allowed_host_and_scheme
from django.utils.translation import gettext as gettext_now
from django.utils.translation import gettext_lazy as _
from django.utils.translation import pgettext_lazy
from unfold.widgets import (
    UnfoldAdminCheckboxSelectMultipleWidget,
    UnfoldAdminSelectWidget,
    UnfoldAdminSplitDateTimeWidget,
    UnfoldAdminTextareaWidget,
    UnfoldAdminTextInputWidget,
    UnfoldBooleanSwitchWidget,
)

from ninefruits.institution.admin_support import render_action_form, show_errors
from ninefruits.offering.enums import SectionStatus
from ninefruits.registration.data import RegistrationOutcome
from ninefruits.registration.enums import HoldType, RuleCode
from ninefruits.term.models import Term

REASON_MAX = 1000


def default_term_id() -> int | None:
    """The term staff most likely work on (the section screens' default)."""
    from ninefruits.offering.admin.sections import default_term_id as section_default

    return section_default()


def term_label(term: Any) -> str:
    return f"{term.name} ({term.code})"


def reason_field() -> forms.CharField:
    return forms.CharField(
        label=pgettext_lazy("common", "Reason"),
        max_length=REASON_MAX,
        widget=UnfoldAdminTextareaWidget(attrs={"rows": 3}),
    )


def term_choices(statuses: tuple[str, ...] | None = None) -> list[tuple[int, str]]:
    terms = Term.objects.order_by("-start_date")
    if statuses is not None:
        terms = terms.filter(status__in=statuses)
    return [(term.pk, term_label(term)) for term in terms]


def find_student_record(user: Any, number: str) -> Any:
    """A student record the user can see, by student number (original ``StudentRecordSelect``)."""
    from ninefruits.person.models import StudentRecord

    record = (
        StudentRecord.objects.visible_to(user)
        .select_related("person")
        .filter(student_number=(number or "").strip())
        .first()
    )
    if record is None:
        raise ValidationError(_("No student record with number %(number)s.") % {"number": number})
    return record


def find_section(term_id: int | None, label: str) -> Any:
    """A section of the term by ``COURSE-SECTION`` (e.g. ``CSE2010-01``)."""
    from ninefruits.offering.models import Section

    course_code, _dash, section_code = (label or "").strip().partition("-")
    section = (
        Section.objects.filter(term_id=term_id, course__code=course_code, section_code=section_code)
        .select_related("course")
        .first()
    )
    if section is None:
        raise ValidationError(gettext_now("Unknown section %(section)s.") % {"section": label})
    return section


class StudentNumberField(forms.CharField):
    def __init__(self, **kwargs: Any) -> None:
        super().__init__(label=_("Student number"), max_length=32, widget=UnfoldAdminTextInputWidget, **kwargs)


class UserForm(forms.Form):
    """Forms that look up rows the signed-in user may see."""

    def __init__(self, *args: Any, user: Any = None, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.user = user

    def clean_student_number(self) -> Any:
        return find_student_record(self.user, self.cleaned_data["student_number"])


def section_choices(term_id: int | None) -> list[tuple[int, str]]:
    from ninefruits.offering.models import Section

    sections = (
        Section.objects.filter(term_id=term_id, status=SectionStatus.PUBLISHED)
        .select_related("course", "version")
        .order_by("course__code", "section_code")
    )
    return [(section.pk, f"{section.label()} {section.version.title or ''}".strip()) for section in sections]


def waivable_rules() -> list[tuple[str, Any]]:
    """Rules staff may waive: every rule except the section state and seats."""
    return [(code.value, code.label) for code in RuleCode if code not in (RuleCode.SECTION_OPEN, RuleCode.CAPACITY)]


class StaffEnrollForm(UserForm):
    """Staff registration: same rules, chosen ones waived with a reason. With a section (the
    section roster) only the student is chosen."""

    student_number = StudentNumberField()
    section_id = forms.TypedChoiceField(
        label=pgettext_lazy("offering", "Section"), coerce=int, required=False, widget=UnfoldAdminSelectWidget
    )
    waive = forms.MultipleChoiceField(
        label=_("Waive rules"), required=False, widget=UnfoldAdminCheckboxSelectMultipleWidget
    )
    waitlist = forms.BooleanField(
        label=_("Add to the waitlist if full"), required=False, widget=UnfoldBooleanSwitchWidget
    )
    reason = reason_field()

    def __init__(self, *args: Any, section: Any = None, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.section = section
        self.fields["waive"].choices = waivable_rules()  # type: ignore[attr-defined]
        if section is not None:
            del self.fields["section_id"]
        else:
            self.fields["section_id"].required = True
            self.fields["section_id"].choices = section_choices(default_term_id())  # type: ignore[attr-defined]

    def chosen_section(self) -> Any:
        from ninefruits.offering.models import Section

        if self.section is not None:
            return self.section
        return Section.objects.select_related("course").get(pk=self.cleaned_data["section_id"])

    def waived(self) -> tuple[RuleCode, ...]:
        return tuple(RuleCode(code) for code in self.cleaned_data.get("waive") or [])


class ReasonForm(forms.Form):
    reason = reason_field()


class ConfirmForm(forms.Form):
    """Nothing to enter: the page asks for confirmation (original ``requiresConfirmation``)."""


def hold_type_choices() -> list[tuple[str, Any]]:
    return list(HoldType.choices)


class PlaceHoldForm(UserForm):
    student_number = StudentNumberField()
    hold_type = forms.ChoiceField(label=_("Hold type"), choices=HoldType.choices, widget=UnfoldAdminSelectWidget)
    blocks_registration = forms.BooleanField(
        label=_("Blocks registration"), required=False, initial=True, widget=UnfoldBooleanSwitchWidget
    )
    blocks_grades = forms.BooleanField(
        label=_("Blocks grade viewing"), required=False, widget=UnfoldBooleanSwitchWidget
    )
    blocks_certificates = forms.BooleanField(
        label=_("Blocks certificates"), required=False, widget=UnfoldBooleanSwitchWidget
    )
    starts_at = forms.SplitDateTimeField(label=_("Starts"), required=False, widget=UnfoldAdminSplitDateTimeWidget)
    ends_at = forms.SplitDateTimeField(label=_("Ends"), required=False, widget=UnfoldAdminSplitDateTimeWidget)
    reason = reason_field()

    def clean(self) -> dict[str, Any]:
        cleaned = super().clean() or {}
        starts, ends = cleaned.get("starts_at"), cleaned.get("ends_at")
        if starts is not None and ends is not None and ends <= starts:
            self.add_error(
                "ends_at",
                gettext_now("The %(attribute)s field must be a date after %(date)s.")
                % {"attribute": _("Ends"), "date": _("Starts")},
            )
        return cleaned


class GrantOverrideForm(UserForm):
    student_number = StudentNumberField()
    term_id = forms.TypedChoiceField(label=_("term"), coerce=int, widget=UnfoldAdminSelectWidget)
    rule_code = forms.ChoiceField(label=_("Rule"), widget=UnfoldAdminSelectWidget)
    section = forms.CharField(
        label=pgettext_lazy("offering", "Section"),
        required=False,
        max_length=64,
        help_text=_("Leave empty to apply to every section of the term."),
        widget=UnfoldAdminTextInputWidget(attrs={"placeholder": "CSE2010-01"}),
    )
    course = forms.CharField(
        label=_("course"),
        required=False,
        max_length=32,
        help_text=_("Leave empty for any course. Ignored when a section is chosen."),
        widget=UnfoldAdminTextInputWidget,
    )
    expires_at = forms.SplitDateTimeField(label=_("Expires"), required=False, widget=UnfoldAdminSplitDateTimeWidget)
    reason = reason_field()

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.fields["term_id"].choices = term_choices(("planned", "published"))  # type: ignore[attr-defined]
        self.fields["term_id"].initial = default_term_id()
        self.fields["rule_code"].choices = [(code.value, code.label) for code in RuleCode.overridable()]  # type: ignore[attr-defined]

    def clean(self) -> dict[str, Any]:
        from ninefruits.curriculum.models import Course

        cleaned = super().clean() or {}
        cleaned["section_obj"] = None
        cleaned["course_obj"] = None
        if cleaned.get("section"):
            try:
                cleaned["section_obj"] = find_section(cleaned.get("term_id"), cleaned["section"])
            except ValidationError as error:
                self.add_error("section", error)
        elif cleaned.get("course"):
            course = Course.objects.filter(code=cleaned["course"].strip()).first()
            if course is None:
                self.add_error("course", gettext_now("Unknown course %(course)s.") % {"course": cleaned["course"]})
            cleaned["course_obj"] = course
        return cleaned


# -- filters --------------------------------------------------------------------------------------
class DefaultTermFilter(admin.SimpleListFilter):
    """The term in session (or the next one) by default; ``all`` for every term."""

    title = _("term")
    parameter_name = "term"
    default_to_current = True
    field = "term_id"

    def lookups(self, request: HttpRequest, model_admin: Any) -> list[tuple[Any, Any]]:
        return [("all", _("All")), *((str(pk), label) for pk, label in term_choices())]

    def value(self) -> Any:
        value = super().value()
        if value is None and self.default_to_current:
            default = default_term_id()
            return str(default) if default is not None else None
        return value

    def choices(self, changelist: Any) -> Any:
        current = self.value()
        for lookup, title in self.lookup_choices:
            yield {
                "selected": current == str(lookup),
                "query_string": changelist.get_query_string({self.parameter_name: lookup}),
                "display": title,
            }

    def queryset(self, request: HttpRequest, queryset: Any) -> Any:
        value = self.value()
        if value in (None, "all"):
            return queryset
        return queryset.filter(**{self.field: value})


class AnyTermFilter(DefaultTermFilter):
    default_to_current = False


class ChoiceFilter(admin.SimpleListFilter):
    """A status-like filter with a default value (``all`` shows everything)."""

    choices_class: Any = None
    default: str | None = None

    def lookups(self, request: HttpRequest, model_admin: Any) -> list[tuple[Any, Any]]:
        return [("all", _("All")), *self.choices_class.choices]

    def value(self) -> Any:
        value = super().value()
        return self.default if value is None else value

    def choices(self, changelist: Any) -> Any:
        current = self.value()
        for lookup, title in self.lookup_choices:
            yield {
                "selected": current == str(lookup),
                "query_string": changelist.get_query_string({self.parameter_name: lookup}),
                "display": title,
            }

    def queryset(self, request: HttpRequest, queryset: Any) -> Any:
        value = self.value()
        if value in (None, "all"):
            return queryset
        return queryset.filter(**{self.parameter_name: value})


class InForceFilter(admin.SimpleListFilter):
    """Holds and overrides in force (default), or ended."""

    title = _("In force")
    parameter_name = "in_force"

    def lookups(self, request: HttpRequest, model_admin: Any) -> list[tuple[Any, Any]]:
        return [("yes", _("Yes")), ("no", _("No")), ("all", _("All"))]

    def value(self) -> Any:
        value = super().value()
        return "yes" if value is None else value

    def choices(self, changelist: Any) -> Any:
        current = self.value()
        for lookup, title in self.lookup_choices:
            yield {
                "selected": current == lookup,
                "query_string": changelist.get_query_string({self.parameter_name: lookup}),
                "display": title,
            }

    def queryset(self, request: HttpRequest, queryset: Any) -> Any:
        value = self.value()
        if value == "all":
            return queryset
        in_force = queryset.model.objects.in_force().values("pk")
        return queryset.filter(pk__in=in_force) if value == "yes" else queryset.exclude(pk__in=in_force)


# -- running actions ------------------------------------------------------------------------------
def safe_next(request: HttpRequest, fallback: str) -> str:
    target = request.POST.get("next") or request.GET.get("next")
    if target and url_has_allowed_host_and_scheme(target, allowed_hosts={request.get_host()}):
        return str(target)
    return fallback


def run_form(
    model_admin: Any,
    request: HttpRequest,
    form: forms.Form,
    title: Any,
    back_url: str,
    perform: Callable[[forms.Form], str | None],
    **extra: Any,
) -> HttpResponse:
    """Shows the form; on a valid POST runs ``perform`` (an action call returning a success
    message) and goes back. Action errors become messages (original ``ShowsActionErrors``)."""
    back = safe_next(request, back_url)
    if request.method == "POST" and form.is_valid():
        try:
            message = perform(form)
        except ValidationError as error:
            show_errors(request, error)
        except PermissionDenied:
            raise
        else:
            if message:
                messages.success(request, message)
            return HttpResponseRedirect(back)
    return render_action_form(model_admin, request, form, title, back, **extra)


def report_outcome(request: HttpRequest, outcome: RegistrationOutcome) -> None:
    """The outcome of a staff registration as a message: its label and the reasons."""
    from ninefruits.registration.enums import AttemptOutcome

    text = " ".join([str(AttemptOutcome(outcome.outcome).label), *outcome.messages()])
    level = messages.SUCCESS if outcome.succeeded() else messages.WARNING
    messages.add_message(request, level, text)
