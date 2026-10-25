"""Instructors and status change types in the admin panel (original Filament
``InstructorResource`` with ``CreateInstructor``, and ``StatusChangeTypeResource``)."""

from __future__ import annotations

from typing import Any, ClassVar

from django import forms
from django.contrib import admin, messages
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.db.models import Q
from django.http import HttpRequest, HttpResponse, HttpResponseRedirect
from django.urls import reverse
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.utils.translation import pgettext_lazy
from unfold.contrib.filters.admin import RadioFilter
from unfold.decorators import display
from unfold.widgets import (
    UnfoldAdminCheckboxSelectMultipleWidget,
    UnfoldAdminDateWidget,
    UnfoldAdminRadioSelectWidget,
    UnfoldAdminSelectWidget,
    UnfoldAdminTextInputWidget,
)

from ninefruits.adminpanel.navigation import NavigationGroup
from ninefruits.i18n.forms import TranslatableFormField
from ninefruits.institution.admin_support import ReferenceAdmin
from ninefruits.organization.models import OrgUnit
from ninefruits.person.enums import EmploymentType, StudentStatus
from ninefruits.person.models import Instructor, Person, StudentStatusChangeType
from ninefruits.security.enums import Permission

from .common import admin_change_url, apply_errors, form_page
from .people import PersonFields


def instructor_fields() -> dict[str, forms.Field]:
    return {
        "employee_number": forms.CharField(
            label=_("Employee number"), max_length=32, widget=UnfoldAdminTextInputWidget
        ),
        "org_unit": forms.ModelChoiceField(
            label=_("Org unit"),
            queryset=OrgUnit.objects.effective_on().order_by("code"),
            widget=UnfoldAdminSelectWidget,
        ),
        "employment_type": forms.ChoiceField(
            label=_("Employment type"), choices=EmploymentType.choices, widget=UnfoldAdminSelectWidget
        ),
        "academic_title": TranslatableFormField(label=_("Academic title"), required=False),
        "hire_date": forms.DateField(label=_("Hire date"), required=False, widget=UnfoldAdminDateWidget),
        "end_date": forms.DateField(label=_("End date"), required=False, widget=UnfoldAdminDateWidget),
    }


def _check_period(form: forms.BaseForm, cleaned: dict[str, Any]) -> None:
    hire, end = cleaned.get("hire_date"), cleaned.get("end_date")
    if hire and end and end < hire:
        form.add_error(
            "end_date",
            _("The %(attribute)s field must be a date after or equal to %(date)s.")
            % {"attribute": _("End date"), "date": _("Hire date")},
        )


class InstructorAdminForm(forms.ModelForm):  # type: ignore[type-arg]
    class Meta:
        model = Instructor
        fields = ("employee_number", "org_unit", "employment_type", "academic_title", "hire_date", "end_date")

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        for name, field in instructor_fields().items():
            self.fields[name] = field

    def clean_employee_number(self) -> str:
        number = str(self.cleaned_data["employee_number"]).strip()
        if Instructor.objects.filter(employee_number=number).exclude(pk=self.instance.pk).exists():
            raise ValidationError(_("The employee number has already been taken."))
        return number

    def clean(self) -> dict[str, Any]:
        cleaned = super().clean() or {}
        _check_period(self, cleaned)
        return cleaned


class NewInstructorForm(PersonFields):
    person_mode = forms.ChoiceField(
        label=_("Person"),
        choices=[("new", _("New person")), ("existing", _("Existing person"))],
        initial="new",
        widget=UnfoldAdminRadioSelectWidget,
    )
    person = forms.ModelChoiceField(
        label=_("Existing person"), queryset=Person.objects.none(), required=False, widget=UnfoldAdminSelectWidget
    )

    def __init__(self, *args: Any, user: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.fields["person"].queryset = (  # type: ignore[attr-defined]
            Person.objects.visible_to(user).not_merged().filter(instructor__isnull=True).order_by("family_name")
        )
        self.add_person_fields(None, prefix="new_person_")
        for name, field in self.fields.items():
            if name.startswith("new_person_"):
                field.required = False
        for name, field in instructor_fields().items():
            self.fields[name] = field

    def clean_employee_number(self) -> str:
        number = str(self.cleaned_data["employee_number"]).strip()
        if Instructor.objects.filter(employee_number=number).exists():
            raise ValidationError(_("The employee number has already been taken."))
        return number

    def clean(self) -> dict[str, Any]:
        cleaned = super().clean() or {}
        if cleaned.get("person_mode") == "existing":
            if cleaned.get("person") is None:
                self.add_error("person", _("This field is required."))
        elif not cleaned.get("new_person_family_name"):
            self.add_error("new_person_family_name", _("This field is required."))
        _check_period(self, cleaned)
        return cleaned


class CurrentInstructorFilter(RadioFilter):
    title = _("Current instructors only")
    parameter_name = "current"

    def lookups(self, request: HttpRequest, model_admin: Any) -> list[tuple[str, Any]]:
        return [("1", _("Yes")), ("0", _("No"))]

    def queryset(self, request: HttpRequest, queryset: Any) -> Any:
        if self.value() in (None, "1"):
            return queryset.filter(Q(end_date__isnull=True) | Q(end_date__gte=timezone.localdate()))
        return queryset


@admin.register(Instructor)
class InstructorAdmin(ReferenceAdmin):
    """Instructors (legacy FACULTY). Person details are edited on the person."""

    permissions: ClassVar[dict[str, str]] = {"change": Permission.INSTRUCTORS_MANAGE}
    navigation_group = NavigationGroup.STUDENT_RECORDS
    navigation_icon = "co_present"
    navigation_order = 40
    import_type = "instructors"
    translated_search_fields = ()
    form = InstructorAdminForm
    list_display = ("employee_number", "name_column", "org_unit", "employment_type", "title_column", "end_date")
    list_filter = (CurrentInstructorFilter,)
    list_select_related = ("person", "org_unit")
    ordering = ("employee_number",)

    def has_view_permission(self, request: HttpRequest, obj: Any = None) -> bool:
        return self.policy_allows(request, "view_any", Instructor)

    def has_add_permission(self, request: HttpRequest, *args: Any) -> bool:
        return self.policy_allows(request, "create", Instructor)

    def has_change_permission(self, request: HttpRequest, obj: Any = None) -> bool:
        return bool(request.user.has_perm(Permission.INSTRUCTORS_MANAGE))

    def has_delete_permission(self, request: HttpRequest, obj: Any = None) -> bool:
        return False

    def get_search_fields(self, request: HttpRequest) -> tuple[str, ...]:
        return ("employee_number",)

    def get_search_results(self, request: HttpRequest, queryset: Any, search_term: str) -> tuple[Any, bool]:
        term = search_term.strip()
        if not term:
            return queryset, False
        return queryset.filter(employee_number__icontains=term) | queryset.filter(
            person__in=Person.objects.search(term).values("pk")
        ), False

    @display(description=pgettext_lazy("people", "Name"))
    def name_column(self, obj: Instructor) -> str:
        return obj.person.display_name()

    @display(description=_("Academic title"))
    def title_column(self, obj: Instructor) -> str:
        return str(obj.academic_title or "-")

    def add_view(self, request: HttpRequest, form_url: str = "", extra_context: Any = None) -> HttpResponse:
        """New instructor for an existing or a new person (original ``CreateInstructor``)."""
        if not self.has_add_permission(request):
            raise PermissionDenied
        form = NewInstructorForm(request.POST or None, user=request.user)
        if request.method == "POST" and form.is_valid():
            data = form.cleaned_data
            try:
                with transaction.atomic():
                    person = (
                        data["person"]
                        if data["person_mode"] == "existing"
                        else Person.objects.create(**form.person_attributes(prefix="new_person_"))
                    )
                    instructor = Instructor.objects.create(
                        person=person,
                        employee_number=data["employee_number"],
                        org_unit=data["org_unit"],
                        employment_type=data["employment_type"],
                        academic_title=data.get("academic_title") or None,
                        hire_date=data.get("hire_date"),
                        end_date=data.get("end_date"),
                    )
            except ValidationError as error:
                apply_errors(form, error)
            else:
                messages.success(request, _("Instructor created."))
                return HttpResponseRedirect(admin_change_url(instructor))
        return form_page(self, request, form, _("New instructor"), reverse("admin:person_instructor_changelist"))


class StatusChangeTypeForm(forms.ModelForm):  # type: ignore[type-arg]
    from_statuses = forms.MultipleChoiceField(
        label=_("Allowed from statuses"), choices=StudentStatus.choices, widget=UnfoldAdminCheckboxSelectMultipleWidget
    )

    class Meta:
        model = StudentStatusChangeType
        fields = ("code", "name", "to_status", "from_statuses", "can_student_request", "sort_order", "is_active")
        field_classes = {"name": TranslatableFormField}

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        if self.instance.pk and self.instance.is_system:
            for name in ("code", "to_status", "from_statuses"):
                self.fields[name].disabled = True

    def clean_code(self) -> str:
        code = str(self.cleaned_data["code"])
        import re

        if not re.fullmatch(r"[a-z][a-z0-9_]*", code):
            raise ValidationError(
                pgettext_lazy("validation.regex", "The %(attribute)s field format is invalid.")
                % {"attribute": pgettext_lazy("reference", "Code")}
            )
        return code


@admin.register(StudentStatusChangeType)
class StudentStatusChangeTypeAdmin(ReferenceAdmin):
    """Kinds of status change. The transition of system kinds is fixed; names and whether
    students may request them are editable."""

    manage_permission = Permission.STUDENT_RECORDS_MANAGE
    navigation_group = NavigationGroup.STUDENT_RECORDS
    navigation_icon = "swap_horiz"
    navigation_order = 70
    form = StatusChangeTypeForm
    list_display = ("code", "name", "to_status_display", "can_student_request", "is_system", "is_active")
    search_fields = ("code",)
    ordering = ("sort_order", "code")

    @display(description=_("New status"))
    def to_status_display(self, obj: StudentStatusChangeType) -> str:
        return str(StudentStatus(obj.to_status).label)

    def has_delete_permission(self, request: HttpRequest, obj: Any = None) -> bool:
        if obj is not None and obj.is_system:
            return False
        return super().has_delete_permission(request, obj)
