"""Sections (original Filament ``Resources/Offering/Sections`` with the meetings, instructors and
seat groups relation managers): staff of the offering unit plan them per term session.

- The list and every page are limited to the user's ``sections.view``/``sections.manage`` scope;
  changing needs ``sections.manage`` covering the section's offering unit.
- Meetings, instructors and seat groups are tabs. Changes there go through the actions, so a room
  or instructor already booked is refused with the name of the other section.
- Status changes (publish, back to draft, cancel with a reason, reopen) are buttons on the page."""

from __future__ import annotations

from datetime import time
from typing import Any, ClassVar

from django import forms
from django.contrib import admin, messages
from django.contrib.admin.options import ActionLocation
from django.core.exceptions import PermissionDenied, ValidationError
from django.db.models import Q
from django.http import HttpRequest, HttpResponse, HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.urls import reverse
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.utils.translation import pgettext, pgettext_lazy
from unfold.admin import StackedInline, TabularInline
from unfold.decorators import action, display
from unfold.forms import BaseDialogForm
from unfold.widgets import (
    UnfoldAdminSelectWidget,
    UnfoldAdminTextareaWidget,
    UnfoldBooleanSwitchWidget,
)

from ninefruits.adminpanel.mixins import CatalogAdmin, CatalogPermissionMixin
from ninefruits.adminpanel.navigation import NavigationGroup
from ninefruits.core.targeting import TargetCriteria
from ninefruits.curriculum.models import Course
from ninefruits.facility.models import Room
from ninefruits.grading.enums import EvaluationMethod
from ninefruits.i18n.fields import I18nSearchText
from ninefruits.institution.admin_support import admin_url, render_action_form, show_errors
from ninefruits.institution.target_criteria_fields import PARTS, TargetCriteriaForm, criteria_fields
from ninefruits.offering.actions import (
    AssignSectionInstructor,
    ChangeSectionStatus,
    CopySections,
    CreateSection,
    SaveSectionMeeting,
    SectionCopyReport,
    UpdateSection,
)
from ninefruits.offering.enums import InstructorRole, SectionStatus
from ninefruits.offering.models import Section, SectionInstructor, SectionMeeting, SectionSeatGroup
from ninefruits.offering.services import summary
from ninefruits.offering.services.timetable import weekday_choices
from ninefruits.organization.models import OrgUnit
from ninefruits.registration.admin.roster import SectionRegistrationMixin
from ninefruits.security.enums import Permission
from ninefruits.term.models import Term, TermSession, TimeSlot

SECTION_PERMISSIONS: dict[str, str] = {
    "view": Permission.SECTIONS_VIEW,
    "add": Permission.SECTIONS_MANAGE,
    "change": Permission.SECTIONS_MANAGE,
    "delete": Permission.SECTIONS_MANAGE,
}

CRITERIA_FIELDSET_PARTS = (
    "year_levels",
    ("admission_year_from", "admission_year_to"),
    "program_ids",
    "org_unit_ids",
)


def default_term_id() -> int | None:
    """The term staff most likely work on: the one in session, else the next one."""
    from ninefruits.term.services import TermResolver

    in_session = TermResolver().in_session()
    if in_session:
        return int(in_session[0].pk)
    return (
        Term.objects.filter(start_date__gte=timezone.localdate())
        .order_by("start_date")
        .values_list("pk", flat=True)
        .first()
    )


def term_label(term: Term) -> str:
    return f"{term.name} ({term.code})"


def term_choices() -> list[tuple[int, str]]:
    return [(term.pk, term_label(term)) for term in Term.objects.order_by("-start_date")]


def session_choices() -> list[tuple[str, list[tuple[int, str]]]]:
    """Sessions grouped by term, for selects (planned and published terms)."""
    groups = []
    terms = (
        Term.objects.filter(status__in=["planned", "published"]).order_by("-start_date").prefetch_related("sessions")
    )
    for term in terms:
        groups.append(
            (
                term_label(term),
                [
                    (session.pk, f"{session.name} {session.start_date:%m-%d}~{session.end_date:%m-%d}")
                    for session in term.sessions.all()
                ],
            )
        )
    return groups


def unit_choices() -> list[tuple[int, str]]:
    return [(unit.pk, str(unit)) for unit in OrgUnit.objects.order_by("code")]


def instructor_choices() -> list[tuple[int, str]]:
    from ninefruits.person.models import Instructor

    rows = [
        (
            instructor.pk,
            f"{instructor.person.display_name()} ({instructor.employee_number}, {instructor.org_unit.name})",
        )
        for instructor in Instructor.objects.current().select_related("person", "org_unit")
    ]
    return sorted(rows, key=lambda row: row[1])


def room_choices() -> list[tuple[int, str]]:
    rooms = Room.objects.filter(is_active=True, is_schedulable=True).select_related("building")
    rows = [
        (room.pk, f"{room.building.code}-{room.code}" + (f" ({room.capacity})" if room.capacity else ""))
        for room in rooms
    ]
    return sorted(rows, key=lambda row: row[1])


def report_message(report: SectionCopyReport, dry_run: bool) -> str:
    values = report.summary()
    title = (
        pgettext(
            "offering",
            "Preview: %(created)s section(s) would be copied, %(skipped)s skipped, %(with_notes)s with notes.",
        )
        if dry_run
        else pgettext("offering", "%(created)s section(s) copied, %(skipped)s skipped, %(with_notes)s with notes.")
    ) % values
    lines = report.lines()
    details = "; ".join(lines[:30]) + ("; …" if len(lines) > 30 else "")
    return f"{title} {details}".strip()


# -- forms ----------------------------------------------------------------------------------------
class CriteriaFormMixin(forms.ModelForm):  # type: ignore[type-arg]
    """Inputs for the eligibility and exclusion criteria (``eligibility__year_levels`` ...)."""

    criteria_prefixes: ClassVar[tuple[str, ...]] = ("eligibility", "exclusion")

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        from ninefruits.institution.target_criteria_fields import _org_unit_choices, _program_choices

        for prefix in self.criteria_prefixes:
            self.fields[f"{prefix}__program_ids"].choices = _program_choices()  # type: ignore[attr-defined]
            self.fields[f"{prefix}__org_unit_ids"].choices = _org_unit_choices()  # type: ignore[attr-defined]
            if self.instance.pk:
                values = TargetCriteria.coerce(getattr(self.instance, prefix)).to_dict()
                for part in PARTS:
                    self.initial.setdefault(f"{prefix}__{part}", values.get(part))

    def criteria(self, prefix: str) -> TargetCriteria:
        data = getattr(self, "cleaned_data", {})
        return TargetCriteria.from_dict({part: data.get(f"{prefix}__{part}") for part in PARTS})

    def clean(self) -> dict[str, Any]:
        cleaned = super().clean() or {}
        for prefix in self.criteria_prefixes:
            start, end = cleaned.get(f"{prefix}__admission_year_from"), cleaned.get(f"{prefix}__admission_year_to")
            if start is not None and end is not None and end < start:
                self.add_error(
                    f"{prefix}__admission_year_to",
                    _("The %(attribute)s field must be greater than or equal to %(value)s.")
                    % {"attribute": _("Admitted until (year)"), "value": _("Admitted from (year)")},
                )
        return cleaned


def declare_criteria_fields(form_class: type[forms.BaseForm], prefixes: tuple[str, ...]) -> None:
    """Declares the criteria inputs on the form class (admin fieldsets need them there)."""
    for prefix in prefixes:
        for name, field in criteria_fields(prefix).items():
            if name.endswith("__academic_standings"):
                continue
            form_class.declared_fields[name] = field  # type: ignore[attr-defined]
            form_class.base_fields[name] = field


class SectionCreateForm(forms.ModelForm):  # type: ignore[type-arg]
    """Original ``CreateSection`` page: the session and course, then the rest on the edit page."""

    term_session_id = forms.TypedChoiceField(
        label=pgettext_lazy("offering", "Session"), coerce=int, widget=UnfoldAdminSelectWidget
    )
    course_id = forms.TypedChoiceField(label=_("course"), coerce=int, widget=UnfoldAdminSelectWidget)

    class Meta:
        model = Section
        fields = (
            "section_code",
            "capacity",
            "evaluation_method",
            "waitlist_capacity",
            "org_unit",
            "instruction_language",
        )

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.fields["term_session_id"].choices = session_choices()  # type: ignore[attr-defined]
        self.fields["course_id"].choices = [  # type: ignore[attr-defined]
            (course.pk, str(course)) for course in Course.objects.filter(is_active=True).order_by("code")
        ]
        self.fields["org_unit"].queryset = OrgUnit.objects.order_by("code")  # type: ignore[attr-defined]
        self.fields["org_unit"].required = False
        self.fields["org_unit"].help_text = _("Unit whose staff manage the section; the course's unit by default.")
        self.fields["evaluation_method"].help_text = _(
            "Absolute (default): instructors enter scores and the grades follow. Relative: instructors give grades "
            "within the institution's grade caps. Instructors ask for a change from the grade entry screen; it cannot "
            "change once grades are submitted."
        )
        self.initial.setdefault("section_code", "01")
        self.initial.setdefault("capacity", 40)
        self.initial.setdefault("evaluation_method", EvaluationMethod.RELATIVE)
        self.order_fields(["term_session_id", "course_id"])

    def clean_section_code(self) -> str:
        return _alpha_dash(self.cleaned_data["section_code"], _("Section number"))

    def _post_clean(self) -> None:
        """The section is created by the CreateSection action."""


def _alpha_dash(value: Any, label: Any) -> str:
    text = str(value)
    if not all(char.isalnum() or char in "-_" for char in text):
        raise ValidationError(
            _("The %(attribute)s field must only contain letters, numbers, dashes, and underscores.")
            % {"attribute": label}
        )
    return text


class SectionForm(CriteriaFormMixin):
    term_session_id = forms.TypedChoiceField(
        label=pgettext_lazy("offering", "Session"),
        coerce=int,
        widget=UnfoldAdminSelectWidget,
        help_text=_("Moving to another session takes its dates and the course version in effect when it starts."),
    )

    class Meta:
        model = Section
        fields = (
            "section_code",
            "capacity",
            "evaluation_method",
            "waitlist_capacity",
            "org_unit",
            "instruction_language",
            "note",
        )

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.fields["term_session_id"].choices = [  # type: ignore[attr-defined]
            (session.pk, str(session)) for session in TermSession.objects.filter(term_id=self.instance.term_id)
        ]
        self.initial.setdefault("term_session_id", self.instance.session_id)
        self.fields["org_unit"].queryset = OrgUnit.objects.order_by("code")  # type: ignore[attr-defined]

    def clean_section_code(self) -> str:
        return _alpha_dash(self.cleaned_data["section_code"], _("Section number"))

    def _post_clean(self) -> None:
        """Changes go through the UpdateSection action."""

    def data_for_action(self) -> dict[str, Any]:
        data = {name: self.cleaned_data.get(name) for name in self.Meta.fields if name in self.cleaned_data}
        data["org_unit_id"] = data.pop("org_unit").pk if data.get("org_unit") else None
        data["term_session_id"] = self.cleaned_data.get("term_session_id")
        data["eligibility"] = self.criteria("eligibility")
        data["exclusion"] = self.criteria("exclusion")
        if data.get("note") is not None and not isinstance(data["note"], dict):
            data["note"] = getattr(data["note"], "translations", data["note"])
        return data


declare_criteria_fields(SectionForm, SectionForm.criteria_prefixes)


class MeetingForm(forms.ModelForm):  # type: ignore[type-arg]
    time_slot = forms.ModelChoiceField(
        label=_("Period"),
        queryset=TimeSlot.objects.none(),
        required=False,
        help_text=_("Fills start and end from a period."),
    )

    class Meta:
        model = SectionMeeting
        fields = ("weekday", "time_slot", "start_time", "end_time", "room", "start_date", "end_date")

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.fields["weekday"] = forms.TypedChoiceField(
            label=_("Day"), choices=weekday_choices(), coerce=int, widget=UnfoldAdminSelectWidget
        )
        self.fields["time_slot"].queryset = TimeSlot.objects.filter(is_active=True).order_by("sort_order")  # type: ignore[attr-defined]
        self.fields["time_slot"].label_from_instance = lambda slot: (  # type: ignore[attr-defined]
            f"{slot.name} {slot.start_time:%H:%M}–{slot.end_time:%H:%M}"
        )
        self.fields["room"].choices = [("", "---------"), *room_choices()]  # type: ignore[attr-defined]
        for name in ("start_time", "end_time", "start_date", "end_date"):
            self.fields[name].required = False
        self.fields["start_date"].help_text = _("Empty: the session's dates.")

    def clean(self) -> dict[str, Any]:
        cleaned = super().clean() or {}
        slot = cleaned.get("time_slot")
        if slot is not None:
            cleaned.setdefault("start_time", None)
            cleaned["start_time"] = cleaned.get("start_time") or slot.start_time
            cleaned["end_time"] = cleaned.get("end_time") or slot.end_time
        required = _("The %(attribute)s field is required.")
        for name, label in (("start_time", pgettext_lazy("offering", "Start")), ("end_time", _("End"))):
            if not cleaned.get(name) and not cleaned.get("DELETE"):
                self.add_error(name, required % {"attribute": label})
        start, end = cleaned.get("start_time"), cleaned.get("end_time")
        if isinstance(start, time) and isinstance(end, time) and end <= start:
            self.add_error("end_time", pgettext("offering", "The end must be after the start."))
        return cleaned

    def _post_clean(self) -> None:
        """Saved through SaveSectionMeeting."""

    def data_for_action(self) -> dict[str, Any]:
        data = self.cleaned_data
        room = data.get("room")
        return {
            "weekday": data["weekday"],
            "start_time": data["start_time"],
            "end_time": data["end_time"],
            "room_id": room.pk if room else None,
            "start_date": data.get("start_date"),
            "end_date": data.get("end_date"),
        }


class InstructorAssignmentForm(forms.ModelForm):  # type: ignore[type-arg]
    class Meta:
        model = SectionInstructor
        fields = ("instructor", "role")

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        choices = instructor_choices()
        if self.instance.pk and self.instance.instructor_id not in {pk for pk, _label in choices}:
            choices.append((self.instance.instructor_id, str(self.instance.instructor)))
        self.fields["instructor"].choices = [("", "---------"), *choices]  # type: ignore[attr-defined]
        if self.instance.pk:
            self.fields["instructor"].disabled = True

    def _post_clean(self) -> None:
        if self.instance.pk:
            super()._post_clean()


class SeatGroupForm(TargetCriteriaForm):
    section: Section | None = None

    class Meta:
        model = SectionSeatGroup
        fields = ("name", "capacity", "releases_at", "sort_order")

    def clean_capacity(self) -> int:
        capacity = int(self.cleaned_data["capacity"])
        if capacity < 0:
            raise ValidationError(
                _("The %(attribute)s field must be at least %(min)s.")
                % {"attribute": pgettext_lazy("offering", "Capacity"), "min": 0}
            )
        return capacity


class SeatGroupFormSet(forms.BaseInlineFormSet):  # type: ignore[type-arg]
    def clean(self) -> None:
        super().clean()
        section = self.instance
        if section is None or section.pk is None:
            return
        total = sum(
            int(form.cleaned_data.get("capacity") or 0)
            for form in self.forms
            if getattr(form, "cleaned_data", None) and not form.cleaned_data.get("DELETE")
        )
        if total > section.capacity:
            raise ValidationError(
                _("Reserved seats together exceed the section capacity (%(capacity)s).")
                % {"capacity": section.capacity}
            )


# -- inlines --------------------------------------------------------------------------------------
class SectionPartInline(CatalogPermissionMixin):
    """Only staff who manage the section change it (``sections.manage`` in its unit's scope)."""

    permissions: ClassVar[dict[str, str]] = SECTION_PERMISSIONS
    extra = 0
    tab = True

    def _manages(self, request: HttpRequest, obj: Any) -> bool:
        return obj is not None and isinstance(obj, Section) and obj.is_manageable_by(request.user)

    def has_view_permission(self, request: HttpRequest, obj: Any = None) -> bool:
        return bool(
            request.user.has_perm(Permission.SECTIONS_VIEW) or request.user.has_perm(Permission.SECTIONS_MANAGE)
        )

    def has_add_permission(self, request: HttpRequest, obj: Any = None) -> bool:
        return self._manages(request, obj)

    def has_change_permission(self, request: HttpRequest, obj: Any = None) -> bool:
        return self._manages(request, obj)

    def has_delete_permission(self, request: HttpRequest, obj: Any = None) -> bool:
        return self._manages(request, obj)


class MeetingInline(SectionPartInline, TabularInline):  # type: ignore[misc]
    """Weekly meetings. A room or instructor already booked at the time is refused with the name
    of the other section."""

    model = SectionMeeting
    form = MeetingForm
    verbose_name = _("meeting")
    verbose_name_plural = _("meeting times")

    def get_queryset(self, request: HttpRequest) -> Any:
        return super().get_queryset(request).select_related("room__building").order_by("weekday", "start_time")


class InstructorInline(SectionPartInline, TabularInline):  # type: ignore[misc]
    """Instructors of a section (several allowed, e.g. team teaching)."""

    model = SectionInstructor
    form = InstructorAssignmentForm
    verbose_name = pgettext_lazy("offering", "Instructors")
    verbose_name_plural = pgettext_lazy("offering", "Instructors")

    def get_queryset(self, request: HttpRequest) -> Any:
        return super().get_queryset(request).select_related("instructor__person")


class SeatGroupInline(SectionPartInline, StackedInline):  # type: ignore[misc]
    """Reserved seats (e.g. 30 for majors) that open to everyone at a set time."""

    model = SectionSeatGroup
    form = SeatGroupForm
    formset = SeatGroupFormSet
    verbose_name = _("seat group")
    verbose_name_plural = _("reserved seats")
    fieldsets = (
        (None, {"fields": ("name", ("capacity", "sort_order"), "releases_at")}),
        (
            _("Students the seats are for"),
            {
                "classes": ("collapse",),
                "fields": tuple(
                    tuple(f"eligibility__{p}" for p in part) if isinstance(part, tuple) else f"eligibility__{part}"
                    for part in CRITERIA_FIELDSET_PARTS
                ),
            },
        ),
    )


# -- filters --------------------------------------------------------------------------------------
class TermFilter(admin.SimpleListFilter):
    """The term in session (or the next one) by default."""

    title = _("term")
    parameter_name = "term"

    def lookups(self, request: HttpRequest, model_admin: Any) -> list[tuple[Any, Any]]:
        return [("all", _("All")), *((str(pk), label) for pk, label in term_choices())]

    def value(self) -> Any:
        value = super().value()
        if value is None:
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
        return queryset.filter(term_id=value)


class OfferingUnitFilter(admin.SimpleListFilter):
    title = _("Offering unit")
    parameter_name = "org_unit"

    def lookups(self, request: HttpRequest, model_admin: Any) -> list[tuple[Any, Any]]:
        return unit_choices()

    def queryset(self, request: HttpRequest, queryset: Any) -> Any:
        return queryset.filter(org_unit_id=self.value()) if self.value() else queryset


class StatusFilter(admin.SimpleListFilter):
    title = pgettext_lazy("offering", "Status")
    parameter_name = "status"

    def lookups(self, request: HttpRequest, model_admin: Any) -> list[tuple[str, Any]]:
        return list(SectionStatus.choices)

    def queryset(self, request: HttpRequest, queryset: Any) -> Any:
        return queryset.filter(status=self.value()) if self.value() else queryset


# -- dialogs --------------------------------------------------------------------------------------
class CancelForm(BaseDialogForm):
    reason = forms.CharField(
        label=pgettext_lazy("common", "Reason"), max_length=1000, widget=UnfoldAdminTextareaWidget(attrs={"rows": 3})
    )


class CopySectionsForm(forms.Form):
    from_term_id = forms.TypedChoiceField(
        label=pgettext_lazy("offering", "Copy from"), coerce=int, widget=UnfoldAdminSelectWidget
    )
    to_term_id = forms.TypedChoiceField(label=_("Copy into"), coerce=int, widget=UnfoldAdminSelectWidget)
    dry_run = forms.BooleanField(
        label=_("Preview only"),
        required=False,
        initial=True,
        help_text=_("Shows the result without saving."),
        widget=UnfoldBooleanSwitchWidget,
    )

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        choices = term_choices()
        self.fields["from_term_id"].choices = choices  # type: ignore[attr-defined]
        self.fields["to_term_id"].choices = choices  # type: ignore[attr-defined]
        self.fields["to_term_id"].initial = default_term_id()

    def clean(self) -> dict[str, Any]:
        cleaned = super().clean() or {}
        if cleaned.get("from_term_id") and cleaned.get("from_term_id") == cleaned.get("to_term_id"):
            self.add_error("to_term_id", _("Choose two different terms."))
        return cleaned


# -- admin ----------------------------------------------------------------------------------------
@admin.register(Section)
class SectionAdmin(SectionRegistrationMixin, CatalogAdmin):
    """Sections (legacy SFOPOBJECT) with instructors, meetings and rooms, eligibility and seat
    groups."""

    permissions = SECTION_PERMISSIONS
    navigation_group = NavigationGroup.CURRICULUM
    navigation_icon = "view_agenda"
    navigation_order = 30
    form = SectionForm
    inlines = (MeetingInline, InstructorInline, SeatGroupInline)
    list_display = (
        "label_column",
        "title_column",
        "credits_column",
        "session_column",
        "instructors_column",
        "schedule_column",
        "capacity_column",
        "status_column",
    )
    list_filter = (TermFilter, OfferingUnitFilter, StatusFilter)
    list_select_related = ("course", "version", "session")
    search_fields = ("course__code",)
    ordering = ("course__code", "section_code")
    list_per_page = 50
    actions_list = ("copy_sections",)
    actions_detail = (
        "open_syllabus",
        "publish",
        "unpublish",
        "cancel_section",
        "reopen",
        # Roster and waitlist (Phase 5, SectionRegistrationMixin).
        *SectionRegistrationMixin.registration_actions_detail,
    )

    # -- access ----------------------------------------------------------------------------------
    def get_queryset(self, request: HttpRequest) -> Any:
        return Section.objects.manageable_by(request.user).select_related("course", "version", "session", "term")

    def has_change_permission(self, request: HttpRequest, obj: Any = None) -> bool:
        if obj is not None:
            return bool(obj.is_manageable_by(request.user))
        return super().has_change_permission(request, obj)

    def has_delete_permission(self, request: HttpRequest, obj: Any = None) -> bool:
        """Only drafts; published sections are cancelled instead."""
        if obj is not None:
            return bool(request.user.has_perm("delete", obj))
        return super().has_delete_permission(request, obj)

    def get_actions(self, request: HttpRequest, action_location: Any = ActionLocation.CHANGE_LIST) -> dict[str, Any]:
        actions = super().get_actions(request, action_location)
        actions.pop("delete_selected", None)
        return actions

    # -- list ------------------------------------------------------------------------------------
    def get_search_results(self, request: HttpRequest, queryset: Any, search_term: str) -> tuple[Any, bool]:
        term = search_term.strip()
        if not term:
            return queryset, False
        matches = (
            Section.objects.annotate(_search=I18nSearchText("version__title"))
            .filter(Q(course__code__istartswith=term) | Q(_search__icontains=term))
            .values("pk")
        )
        return queryset.filter(pk__in=matches), False

    def changelist_view(self, request: HttpRequest, extra_context: dict[str, Any] | None = None) -> Any:
        self._list_cache: dict[str, Any] | None = None
        return super().changelist_view(request, extra_context)

    def _cache(self, obj: Section) -> dict[str, Any]:
        cache = getattr(self, "_list_cache", None)
        if cache is None or obj.pk not in cache.get("ids", set()):
            ids = getattr(self, "_page_ids", None) or [obj.pk]
            cache = {"ids": set(ids), "instructors": {}, "meetings": {}}
            for assignment in SectionInstructor.objects.filter(section_id__in=ids).select_related("instructor__person"):
                cache["instructors"].setdefault(assignment.section_id, []).append(
                    assignment.instructor.person.display_name()
                )
            for meeting in SectionMeeting.objects.filter(section_id__in=ids).select_related("room__building"):
                cache["meetings"].setdefault(meeting.section_id, []).append(meeting)
            self._list_cache = cache
        return cache

    def get_changelist_instance(self, request: HttpRequest) -> Any:
        changelist = super().get_changelist_instance(request)
        self._page_ids = [row.pk for row in changelist.result_list]
        self._list_cache = None
        return changelist

    @display(description=pgettext_lazy("offering", "Section"), ordering="course__code")
    def label_column(self, obj: Section) -> str:
        return obj.label()

    @display(description=pgettext_lazy("curriculum", "Title"))
    def title_column(self, obj: Section) -> str:
        return str(obj.version.title or "")

    @display(description=pgettext_lazy("curriculum", "Credits"))
    def credits_column(self, obj: Section) -> str:
        return str(obj.version.credits)

    @display(description=pgettext_lazy("offering", "Session"), label=True)
    def session_column(self, obj: Section) -> str:
        return obj.session.code

    @display(description=pgettext_lazy("offering", "Instructors"))
    def instructors_column(self, obj: Section) -> str:
        return ", ".join(self._cache(obj)["instructors"].get(obj.pk, [])) or "-"

    @display(description=_("Schedule"))
    def schedule_column(self, obj: Section) -> str:
        meetings = sorted(self._cache(obj)["meetings"].get(obj.pk, []), key=lambda m: (m.weekday, m.start_time))
        return summary(meetings) or "-"

    @display(description=pgettext_lazy("offering", "Capacity"))
    def capacity_column(self, obj: Section) -> str:
        return f"{obj.enrolled_count} / {obj.capacity}"

    @display(
        description=pgettext_lazy("offering", "Status"),
        label={
            SectionStatus.DRAFT.label: "info",
            SectionStatus.PUBLISHED.label: "success",
            SectionStatus.CANCELLED.label: "danger",
        },
    )
    def status_column(self, obj: Section) -> str:
        return str(SectionStatus(obj.status).label)

    # -- forms -----------------------------------------------------------------------------------
    def get_form(self, request: HttpRequest, obj: Any = None, change: bool = False, **kwargs: Any) -> Any:
        if obj is None:
            kwargs["form"] = SectionCreateForm
            kwargs["fields"] = SectionCreateForm.Meta.fields
        return super().get_form(request, obj, change=change, **kwargs)

    def get_fieldsets(self, request: HttpRequest, obj: Any = None) -> Any:
        if obj is None:
            return (
                (
                    None,
                    {
                        "fields": (
                            "term_session_id",
                            "course_id",
                            ("section_code", "capacity"),
                            ("evaluation_method", "waitlist_capacity"),
                            "org_unit",
                            "instruction_language",
                        )
                    },
                ),
            )
        return (
            *self._section_fieldsets(),
            *self.registration_fieldsets(request, obj),
        )

    def _section_fieldsets(self) -> tuple[Any, ...]:
        def criteria(prefix: str) -> tuple[Any, ...]:
            return tuple(
                tuple(f"{prefix}__{p}" for p in part) if isinstance(part, tuple) else f"{prefix}__{part}"
                for part in CRITERIA_FIELDSET_PARTS
            )

        return (
            (
                None,
                {
                    "fields": (
                        "course_display",
                        "term_session_id",
                        ("section_code", "capacity"),
                        ("evaluation_method", "waitlist_capacity"),
                        "org_unit",
                        "instruction_language",
                        "note",
                        "status_display",
                    )
                },
            ),
            (
                _("Who may register"),
                {
                    "classes": ("collapse",),
                    "description": _("Empty: everyone. Registration (Phase 5) checks it."),
                    "fields": criteria("eligibility"),
                },
            ),
            (
                _("Who may not register"),
                {
                    "classes": ("collapse",),
                    "description": _(
                        "Students matching this cannot register, e.g. the course's own majors for a general course."
                    ),
                    "fields": criteria("exclusion"),
                },
            ),
        )

    def get_readonly_fields(self, request: HttpRequest, obj: Any = None) -> Any:
        if obj is None:
            return ()
        return ("course_display", "status_display", *self.registration_readonly_fields)

    def get_inlines(self, request: HttpRequest, obj: Any) -> Any:
        return self.inlines if obj is not None else ()

    @display(description=_("course"))
    def course_display(self, obj: Section) -> str:
        return f"{obj.label()} {obj.version.title} ({obj.version.credits}) · {term_label(obj.term)}"

    @display(description=pgettext_lazy("offering", "Status"))
    def status_display(self, obj: Section) -> str:
        return str(SectionStatus(obj.status).label)

    def get_changeform_initial_data(self, request: HttpRequest) -> dict[str, Any]:
        return {"section_code": "01", "capacity": 40, **super().get_changeform_initial_data(request)}

    def save_model(self, request: HttpRequest, obj: Section, form: Any, change: bool) -> None:
        if not change:
            data = dict(form.cleaned_data)
            session = get_object_or_404(TermSession, pk=data.pop("term_session_id"))
            course = get_object_or_404(Course, pk=data.pop("course_id"))
            unit = data.pop("org_unit", None)
            data["org_unit_id"] = unit.pk if unit else None
            created = CreateSection()(session, course, data, request.user)
            for field in created._meta.concrete_fields:
                setattr(obj, field.attname, getattr(created, field.attname))
            obj._state.adding = False
            return
        UpdateSection()(obj, form.data_for_action(), request.user)

    def _changeform_view(self, request: HttpRequest, object_id: Any, form_url: str, extra_context: Any) -> Any:
        """Action errors (section number taken, no course version, capacity below registrations)
        become form errors."""
        try:
            return super()._changeform_view(request, object_id, form_url, extra_context)
        except ValidationError as error:
            show_errors(request, error)
            url = request.get_full_path()
            return HttpResponseRedirect(url)
        except PermissionDenied:
            raise

    def save_formset(self, request: HttpRequest, form: Any, formset: Any, change: bool) -> None:
        section: Section = form.instance
        model = formset.model
        # Read by the admin change message.
        formset.new_objects, formset.changed_objects, formset.deleted_objects = [], [], []
        if model is SectionMeeting:
            self._save_meetings(request, section, formset)
        elif model is SectionInstructor:
            self._save_instructors(request, section, formset)
        else:
            super().save_formset(request, form, formset, change)

    def _save_meetings(self, request: HttpRequest, section: Section, formset: Any) -> None:
        for meeting_form in formset.forms:
            data = getattr(meeting_form, "cleaned_data", None)
            if not data:
                continue
            instance = meeting_form.instance
            if data.get("DELETE"):
                if instance.pk:
                    instance.delete()
                continue
            if instance.pk and not meeting_form.has_changed():
                continue
            try:
                SaveSectionMeeting()(
                    section, meeting_form.data_for_action(), request.user, instance if instance.pk else None
                )
            except ValidationError as error:
                show_errors(request, error)

    def _save_instructors(self, request: HttpRequest, section: Section, formset: Any) -> None:
        for assignment_form in formset.forms:
            data = getattr(assignment_form, "cleaned_data", None)
            if not data:
                continue
            instance = assignment_form.instance
            if data.get("DELETE"):
                if instance.pk:
                    instance.delete()
                continue
            if instance.pk:
                if assignment_form.has_changed():
                    instance.role = data["role"]
                    instance.save(update_fields=["role", "updated_at"])
                continue
            try:
                AssignSectionInstructor()(section, data["instructor"], InstructorRole(data["role"]), request.user)
            except ValidationError as error:
                show_errors(request, error)

    def response_add(self, request: HttpRequest, obj: Section, post_url_continue: str | None = None) -> HttpResponse:
        if "_addanother" not in request.POST and "_popup" not in request.POST:
            return HttpResponseRedirect(admin_url(obj))
        return super().response_add(request, obj, post_url_continue)

    # -- status buttons --------------------------------------------------------------------------
    def _status_permission(self, request: HttpRequest, object_id: Any, allowed: tuple[SectionStatus, ...]) -> bool:
        section = Section.objects.filter(pk=object_id).first() if object_id is not None else None
        if section is None:
            return bool(request.user.has_perm(Permission.SECTIONS_MANAGE))
        return section.status in allowed and section.is_manageable_by(request.user)

    def has_publish_permission(self, request: HttpRequest, object_id: Any = None) -> bool:
        return self._status_permission(request, object_id, (SectionStatus.DRAFT,))

    def has_unpublish_permission(self, request: HttpRequest, object_id: Any = None) -> bool:
        return self._status_permission(request, object_id, (SectionStatus.PUBLISHED,))

    def has_cancel_section_permission(self, request: HttpRequest, object_id: Any = None) -> bool:
        return self._status_permission(request, object_id, (SectionStatus.DRAFT, SectionStatus.PUBLISHED))

    def has_reopen_permission(self, request: HttpRequest, object_id: Any = None) -> bool:
        return self._status_permission(request, object_id, (SectionStatus.CANCELLED,))

    def _change_status(
        self, request: HttpRequest, object_id: Any, status: SectionStatus, reason: str | None = None
    ) -> HttpResponse:
        section = get_object_or_404(Section, pk=object_id)
        try:
            ChangeSectionStatus()(section, status, request.user, reason)
        except ValidationError as error:
            show_errors(request, error)
        else:
            messages.success(request, pgettext("offering", "Section is now %(status)s.") % {"status": status.label})
        return HttpResponseRedirect(admin_url(section))

    @action(description=_("Publish"), url_path="publish", permissions=["publish"], icon="visibility")
    def publish(self, request: HttpRequest, object_id: Any) -> HttpResponse:
        return self._change_status(request, object_id, SectionStatus.PUBLISHED)

    @action(description=_("Back to draft"), url_path="unpublish", permissions=["unpublish"], icon="visibility_off")
    def unpublish(self, request: HttpRequest, object_id: Any) -> HttpResponse:
        return self._change_status(request, object_id, SectionStatus.DRAFT)

    @action(
        description=_("Cancel section"),
        url_path="cancel",
        permissions=["cancel_section"],
        icon="cancel",
        dialog={"title": _("Cancel section"), "form_class": CancelForm},
    )
    def cancel_section(self, request: HttpRequest, form: CancelForm, object_id: Any) -> HttpResponse:
        return self._change_status(request, object_id, SectionStatus.CANCELLED, form.cleaned_data.get("reason"))

    @action(description=_("Reopen"), url_path="reopen", permissions=["reopen"], icon="undo")
    def reopen(self, request: HttpRequest, object_id: Any) -> HttpResponse:
        return self._change_status(request, object_id, SectionStatus.DRAFT)

    def has_open_syllabus_permission(self, request: HttpRequest, object_id: Any = None) -> bool:
        section = Section.objects.filter(pk=object_id).first() if object_id is not None else None
        return section is None or bool(request.user.has_perm("edit_syllabus", section))

    @action(description=_("Syllabus"), url_path="syllabus", permissions=["open_syllabus"], icon="description")
    def open_syllabus(self, request: HttpRequest, object_id: Any) -> HttpResponse:
        return HttpResponseRedirect(reverse("portal:syllabus_edit", args=[object_id]))

    # -- copy from another term ------------------------------------------------------------------
    def has_copy_sections_permission(self, request: HttpRequest) -> bool:
        return bool(request.user.has_perm(Permission.SECTIONS_MANAGE))

    @action(
        description=_("Copy from another term"),
        url_path="copy-sections",
        permissions=["copy_sections"],
        icon="content_copy",
    )
    def copy_sections(self, request: HttpRequest) -> HttpResponse:
        form = CopySectionsForm(request.POST or None)
        back = reverse("admin:offering_section_changelist")
        if request.method == "POST" and form.is_valid():
            dry_run = bool(form.cleaned_data.get("dry_run"))
            source = get_object_or_404(Term, pk=form.cleaned_data["from_term_id"])
            target = get_object_or_404(Term, pk=form.cleaned_data["to_term_id"])
            try:
                report = CopySections()(source, target, request.user, dry_run=dry_run)
            except ValidationError as error:
                show_errors(request, error)
            else:
                messages.success(request, report_message(report, dry_run))
                return HttpResponseRedirect(f"{back}?term={target.pk}")
        return render_action_form(
            self,
            request,
            form,
            _("Copy from another term"),
            back,
            description=_(
                "Copies sections that were not cancelled, in your scope, as drafts: instructors still employed, "
                "meetings with rooms (left out if the room is now taken), reserved seats and syllabus drafts. "
                "Sessions are matched by code."
            ),
        )
