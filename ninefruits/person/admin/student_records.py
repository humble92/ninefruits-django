"""Student records in the admin panel (original Filament ``StudentRecordResource`` with
``RegisterStudentRecord``, ``ViewStudentRecord`` header actions and the status changes,
advisors and second majors relation managers).

One record per admission. The status changes only through status changes, never by editing
(porting-plan 8). Department staff see the records of their scope only (``visible_to`` and row
level security); opening another department's record is a 404."""

from __future__ import annotations

from typing import Any, ClassVar

from django import forms
from django.contrib import admin, messages
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.http import HttpRequest, HttpResponse, HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.urls import path, reverse
from django.utils import timezone
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _
from django.utils.translation import pgettext_lazy
from unfold.admin import TabularInline
from unfold.contrib.filters.admin import ChoicesDropdownFilter, RelatedDropdownFilter
from unfold.decorators import action, display
from unfold.widgets import (
    UnfoldAdminDateWidget,
    UnfoldAdminIntegerFieldWidget,
    UnfoldAdminRadioSelectWidget,
    UnfoldAdminSelectWidget,
    UnfoldAdminTextInputWidget,
)

from ninefruits.adminpanel.mixins import CatalogPermissionMixin
from ninefruits.adminpanel.navigation import NavigationGroup
from ninefruits.certificate.admin.student_record import IssueCertificateActionMixin
from ninefruits.graduation.admin.student_record import DegreeAuditActionsMixin
from ninefruits.institution.admin_support import ReferenceAdmin
from ninefruits.organization.models import Program
from ninefruits.person.actions import AssignAdvisor, EndAdditionalProgram, RecordStatusChange, RegisterStudent
from ninefruits.person.enums import AdditionalProgramRole, AdvisorRole, StudentStatus
from ninefruits.person.models import (
    AdvisorAssignment,
    Instructor,
    Person,
    StudentRecord,
    StudentRecordProgram,
    StudentStatusChange,
    StudentStatusChangeType,
)
from ninefruits.security.enums import Permission

from .common import admin_change_url, apply_errors, form_page, reason_field, record_changes
from .people import PersonFields


def _admission_types() -> Any:
    from ninefruits.institution.models import LookupValue

    return LookupValue.objects.of_type("admission_type").filter(is_active=True)


def _terms() -> Any:
    from ninefruits.term.models import Term

    return Term.objects.order_by("-start_date")


class TagsField(forms.CharField):
    """Comma separated free labels stored as a JSON array."""

    def prepare_value(self, value: Any) -> Any:
        if isinstance(value, list):
            return ", ".join(str(tag) for tag in value)
        return value

    def to_python(self, value: Any) -> list[str] | None:
        if isinstance(value, list):
            return [str(tag) for tag in value] or None
        text = super().to_python(value)
        tags = [tag.strip() for tag in str(text or "").split(",") if tag.strip()]
        return list(dict.fromkeys(tags)) or None


def record_fields() -> dict[str, forms.Field]:
    """Editable details (original ``StudentRecordResource::recordFields``)."""
    return {
        "catalog_year": forms.IntegerField(
            label=_("Catalog year"),
            min_value=1950,
            max_value=2200,
            required=False,
            widget=UnfoldAdminIntegerFieldWidget,
            help_text=_("Year of the curriculum that applies to this student, usually the admission year."),
        ),
        "year_level": forms.IntegerField(
            label=pgettext_lazy("people", "Year"),
            min_value=1,
            max_value=10,
            initial=1,
            widget=UnfoldAdminIntegerFieldWidget,
        ),
        "admission_type": forms.ModelChoiceField(
            label=_("Admission type"), queryset=_admission_types(), required=False, widget=UnfoldAdminSelectWidget
        ),
        "admission_term": forms.ModelChoiceField(
            label=_("Admission term"), queryset=_terms(), required=False, widget=UnfoldAdminSelectWidget
        ),
        "institutional_email": forms.EmailField(
            label=_("School email"),
            required=False,
            max_length=255,
            widget=UnfoldAdminTextInputWidget,
            help_text=_("School email address. Used to link school sign-in (SSO) accounts automatically when enabled."),
        ),
        "tags": TagsField(
            label=_("Tags"),
            required=False,
            widget=UnfoldAdminTextInputWidget,
            help_text=_("Free labels for grouping, e.g. scholarship programs."),
        ),
    }


class StudentRecordAdminForm(forms.ModelForm):  # type: ignore[type-arg]
    class Meta:
        model = StudentRecord
        fields = ("catalog_year", "year_level", "admission_type", "admission_term", "institutional_email", "tags")

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        for name, field in record_fields().items():
            field.initial = self.fields[name].initial if name in self.fields else field.initial
            self.fields[name] = field
        self.fields["catalog_year"].required = True


class RegisterStudentForm(PersonFields):
    """A new admission: an existing person (e.g. a returning graduate) or a new one."""

    person_mode = forms.ChoiceField(
        label=_("Person"),
        choices=[("new", _("New person")), ("existing", _("Existing person"))],
        initial="new",
        widget=UnfoldAdminRadioSelectWidget,
    )
    person = forms.ModelChoiceField(
        label=_("Existing person"), queryset=Person.objects.none(), required=False, widget=UnfoldAdminSelectWidget
    )
    program = forms.ModelChoiceField(
        label=pgettext_lazy("security", "Program"), queryset=Program.objects.none(), widget=UnfoldAdminSelectWidget
    )
    admission_date = forms.DateField(label=_("Admission date"), widget=UnfoldAdminDateWidget)
    student_number = forms.CharField(
        label=_("Student number"),
        max_length=32,
        required=False,
        widget=UnfoldAdminTextInputWidget,
        help_text=_("Leave empty to generate one with the student number pattern."),
    )

    def __init__(self, *args: Any, user: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.fields["person"].queryset = Person.objects.visible_to(user).not_merged().order_by("family_name")  # type: ignore[attr-defined]
        self.fields["program"].queryset = Program.objects.effective_on().order_by("code")  # type: ignore[attr-defined]
        self.initial.setdefault("admission_date", timezone.localdate())
        self.add_person_fields(None, prefix="new_person_")
        for name, field in record_fields().items():
            self.fields[name] = field
        for name, field in self.fields.items():
            if name.startswith("new_person_"):
                field.required = False

    def clean(self) -> dict[str, Any]:
        cleaned = super().clean() or {}
        if cleaned.get("person_mode") == "existing":
            if cleaned.get("person") is None:
                self.add_error("person", _("This field is required."))
        elif not cleaned.get("new_person_family_name"):
            self.add_error("new_person_family_name", _("This field is required."))
        return cleaned


class StatusChangeInline(CatalogPermissionMixin, TabularInline):  # type: ignore[misc]
    """Status history of the record (requests and decisions). Read only: decisions are made in
    the status change queue, staff changes with "Record status change"."""

    model = StudentStatusChange
    extra = 0
    tab = True
    can_delete = False
    fields = ("requested_at", "type", "to_status", "effective_date", "status", "reason", "requested_by", "decided_by")
    readonly_fields = fields
    verbose_name = _("status change")
    verbose_name_plural = _("status changes")

    def has_view_permission(self, request: HttpRequest, obj: Any = None) -> bool:
        return True

    def has_add_permission(self, request: HttpRequest, obj: Any = None) -> bool:
        return False

    def has_change_permission(self, request: HttpRequest, obj: Any = None) -> bool:
        return False

    def get_queryset(self, request: HttpRequest) -> Any:
        return super().get_queryset(request).select_related("type", "requested_by", "decided_by")


class AdvisorAssignmentInline(CatalogPermissionMixin, TabularInline):  # type: ignore[misc]
    model = AdvisorAssignment
    extra = 0
    tab = True
    can_delete = False
    fields = ("instructor", "role", "start_date", "end_date")
    readonly_fields = fields
    verbose_name = _("advisor")
    verbose_name_plural = _("advisors")

    def has_view_permission(self, request: HttpRequest, obj: Any = None) -> bool:
        return True

    def has_add_permission(self, request: HttpRequest, obj: Any = None) -> bool:
        return False

    def has_change_permission(self, request: HttpRequest, obj: Any = None) -> bool:
        return False

    def get_queryset(self, request: HttpRequest) -> Any:
        return super().get_queryset(request).select_related("instructor__person")


class AdditionalProgramInline(CatalogPermissionMixin, TabularInline):  # type: ignore[misc]
    """Second majors and minors. Added by approving an application; ending one needs a reason."""

    model = StudentRecordProgram
    extra = 0
    tab = True
    can_delete = False
    fields = ("program", "role", "start_date", "end_date", "end_link")
    readonly_fields = fields
    verbose_name = _("second major or minor")
    verbose_name_plural = _("second majors and minors")

    def has_view_permission(self, request: HttpRequest, obj: Any = None) -> bool:
        return True

    def has_add_permission(self, request: HttpRequest, obj: Any = None) -> bool:
        return False

    def has_change_permission(self, request: HttpRequest, obj: Any = None) -> bool:
        return False

    def get_formset(self, request: HttpRequest, obj: Any = None, **kwargs: Any) -> Any:
        self._request = request
        return super().get_formset(request, obj, **kwargs)

    @admin.display(description="")
    def end_link(self, obj: StudentRecordProgram) -> str:
        request = getattr(self, "_request", None)
        if obj.pk is None or obj.end_date is not None or request is None:
            return ""
        if not (
            obj.student_record.is_manageable_by(request.user)
            or obj.program.is_additional_program_decidable_by(request.user)
        ):
            return ""
        url = reverse("admin:person_studentrecord_end_program", args=[obj.student_record_id, obj.pk])
        return format_html('<a href="{}" class="text-red-600 underline">{}</a>', url, _("End"))


class RecordStatusChangeForm(forms.Form):
    change_type = forms.ModelChoiceField(
        label=_("Change type"), queryset=StudentStatusChangeType.objects.none(), widget=UnfoldAdminSelectWidget
    )
    effective_date = forms.DateField(label=pgettext_lazy("people", "Effective date"), widget=UnfoldAdminDateWidget)
    reason = reason_field(2000)

    def __init__(self, *args: Any, record: StudentRecord, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        applicable = [
            change_type.pk
            for change_type in StudentStatusChangeType.objects.filter(is_active=True)
            if change_type.applies_from(record.status)
        ]
        self.fields["change_type"].queryset = StudentStatusChangeType.objects.filter(pk__in=applicable)  # type: ignore[attr-defined]
        self.initial.setdefault("effective_date", timezone.localdate())


class AssignAdvisorForm(forms.Form):
    instructor = forms.ModelChoiceField(
        label=pgettext_lazy("people", "Advisor"), queryset=Instructor.objects.none(), widget=UnfoldAdminSelectWidget
    )
    role = forms.ChoiceField(
        label=_("Advisor role"),
        choices=AdvisorRole.choices,
        initial=AdvisorRole.PRIMARY,
        widget=UnfoldAdminSelectWidget,
    )
    start_date = forms.DateField(label=_("Start date"), widget=UnfoldAdminDateWidget)

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.fields["instructor"].queryset = (  # type: ignore[attr-defined]
            Instructor.objects.current().select_related("person").order_by("employee_number")
        )
        self.initial.setdefault("start_date", timezone.localdate())


class EndProgramForm(forms.Form):
    end_date = forms.DateField(label=_("End date"), widget=UnfoldAdminDateWidget)
    reason = reason_field()

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.initial.setdefault("end_date", timezone.localdate())


@admin.register(StudentRecord)
class StudentRecordAdmin(DegreeAuditActionsMixin, IssueCertificateActionMixin, ReferenceAdmin):
    permissions: ClassVar[dict[str, str]] = {
        "view": Permission.STUDENT_RECORDS_VIEW,
        "add": Permission.STUDENT_RECORDS_MANAGE,
    }
    navigation_group = NavigationGroup.STUDENT_RECORDS
    navigation_icon = "school"
    navigation_order = 10
    form = StudentRecordAdminForm
    list_display = ("student_number", "name_column", "program", "year_level", "status_badge", "admission_date")
    list_filter = (("status", ChoicesDropdownFilter), ("program", RelatedDropdownFilter), "year_level")
    list_filter_submit = True
    list_select_related = ("person", "program")
    ordering = ("-student_number",)
    show_full_result_count = False
    inlines = (StatusChangeInline, AdvisorAssignmentInline, AdditionalProgramInline)
    # issue_certificate: Phase 8 (IssueCertificateActionMixin); degree_audit, waive_requirement:
    # Phase 11 (DegreeAuditActionsMixin).
    actions_detail = (
        "record_status_change",
        "assign_advisor",
        "degree_audit",
        "waive_requirement",
        "issue_certificate",
        "grade_report",
    )
    change_form_after_template = "person/admin/history.html"
    import_type = "students"
    translated_search_fields = ()
    summary_fields = (
        "student_number",
        "person_link",
        "status_badge",
        "program",
        "org_unit",
        "admission_date",
        "graduation_date",
    )

    # -- permissions (original StudentRecordPolicy) ----------------------------------------------
    def has_view_permission(self, request: HttpRequest, obj: Any = None) -> bool:
        if obj is not None:
            return bool(request.user.has_perm("view", obj))
        return bool(request.user.has_perm("view_any", StudentRecord))

    def has_add_permission(self, request: HttpRequest, *args: Any) -> bool:
        return bool(request.user.has_perm("create", StudentRecord))

    def has_change_permission(self, request: HttpRequest, obj: Any = None) -> bool:
        if obj is None:
            return bool(request.user.has_perm(Permission.STUDENT_RECORDS_MANAGE))
        return bool(request.user.has_perm("update", obj))

    def has_delete_permission(self, request: HttpRequest, obj: Any = None) -> bool:
        """Student records are never deleted; status changes end them."""
        return False

    # -- list -----------------------------------------------------------------------------------
    def get_search_fields(self, request: HttpRequest) -> tuple[str, ...]:
        return ("student_number",)

    def get_search_results(self, request: HttpRequest, queryset: Any, search_term: str) -> tuple[Any, bool]:
        term = search_term.strip()
        if not term:
            return queryset, False
        people = Person.objects.search(term).values("pk")
        return queryset.filter(student_number__icontains=term) | queryset.filter(person__in=people), False

    @display(description=pgettext_lazy("people", "Name"))
    def name_column(self, obj: StudentRecord) -> str:
        return obj.person.display_name()

    @display(description=pgettext_lazy("people", "Status"), label=True)
    def status_badge(self, obj: StudentRecord) -> str:
        return str(StudentStatus(obj.status).label)

    @display(description=_("Person"))
    def person_link(self, obj: StudentRecord) -> Any:
        return format_html(
            '<a class="underline" href="{}">{}</a>', admin_change_url(obj.person), obj.person.display_name()
        )

    # -- detail ---------------------------------------------------------------------------------
    def get_fieldsets(self, request: HttpRequest, obj: Any = None) -> Any:
        editable = ("catalog_year", "year_level", "admission_type", "admission_term", "institutional_email", "tags")
        return [
            (_("Student record"), {"fields": self.summary_fields}),
            (_("Details"), {"fields": editable}),
        ]

    def get_readonly_fields(self, request: HttpRequest, obj: Any = None) -> Any:
        if obj is not None and not self.has_change_permission(request, obj):
            return (
                *self.summary_fields,
                "catalog_year",
                "year_level",
                "admission_type",
                "admission_term",
                "institutional_email",
                "tags",
            )
        return self.summary_fields

    def change_view(self, request: HttpRequest, object_id: str, form_url: str = "", extra_context: Any = None) -> Any:
        extra_context = extra_context or {}
        record = self.get_object(request, object_id)
        if record is not None:
            extra_context["change_history"] = record_changes(
                [
                    ("student_records", [record.pk]),
                    ("student_status_changes", record.status_changes.values_list("pk", flat=True)),
                    ("advisor_assignments", record.advisor_assignments.values_list("pk", flat=True)),
                    ("student_record_programs", record.additional_programs.values_list("pk", flat=True)),
                ]
            )
            extra_context["can_view_audit"] = request.user.has_perm(Permission.AUDIT_RECORDS_VIEW)
        return super().change_view(request, object_id, form_url, extra_context)

    def add_view(self, request: HttpRequest, form_url: str = "", extra_context: Any = None) -> HttpResponse:
        """Register student (original ``RegisterStudentRecord``)."""
        if not self.has_add_permission(request):
            raise PermissionDenied
        form = RegisterStudentForm(request.POST or None, user=request.user)
        if request.method == "POST" and form.is_valid():
            data = form.cleaned_data
            try:
                with transaction.atomic():
                    if data["person_mode"] == "existing":
                        person = data["person"]
                    else:
                        person = Person.objects.create(**form.person_attributes(prefix="new_person_"))
                    record = RegisterStudent().handle(
                        person,
                        data["program"],
                        {
                            "admission_date": data["admission_date"],
                            "catalog_year": data.get("catalog_year") or data["admission_date"].year,
                            "year_level": data.get("year_level") or 1,
                            "admission_type_id": data["admission_type"].pk if data.get("admission_type") else None,
                            "admission_term_id": data["admission_term"].pk if data.get("admission_term") else None,
                            "institutional_email": data.get("institutional_email"),
                            "student_number": data.get("student_number"),
                            "tags": data.get("tags"),
                        },
                        request.user,
                    )
            except ValidationError as error:
                apply_errors(form, error)
            else:
                messages.success(request, _("Student registered."))
                return HttpResponseRedirect(admin_change_url(record))
        return form_page(
            self,
            request,
            form,
            _("Register student"),
            reverse("admin:person_studentrecord_changelist"),
        )

    # -- detail actions (original ViewStudentRecord header actions) ------------------------------
    def _record(self, request: HttpRequest, object_id: Any) -> StudentRecord:
        return get_object_or_404(StudentRecord.objects.visible_to(request.user), pk=object_id)

    def has_record_status_change_permission(self, request: HttpRequest, object_id: Any = None) -> bool:
        if object_id is None:
            return False
        record = StudentRecord.objects.visible_to(request.user).filter(pk=object_id).first()
        return record is not None and request.user.has_perm("change_status", record)

    def has_assign_advisor_permission(self, request: HttpRequest, object_id: Any = None) -> bool:
        if object_id is None:
            return False
        record = StudentRecord.objects.visible_to(request.user).filter(pk=object_id).first()
        return record is not None and request.user.has_perm("assign_advisor", record)

    @action(
        description=_("Record status change"),
        url_path="record-status-change",
        permissions=["record_status_change"],
        icon="sync_alt",
    )
    def record_status_change(self, request: HttpRequest, object_id: Any) -> HttpResponse:
        record = self._record(request, object_id)
        form = RecordStatusChangeForm(request.POST or None, record=record)
        if request.method == "POST" and form.is_valid():
            data = form.cleaned_data
            try:
                RecordStatusChange().handle(
                    record, data["change_type"], data["effective_date"], data["reason"], request.user
                )
            except ValidationError as error:
                apply_errors(form, error)
            else:
                messages.success(request, _("Status change recorded."))
                return HttpResponseRedirect(admin_change_url(record))
        return form_page(self, request, form, _("Record status change"), admin_change_url(record), subtitle=str(record))

    def has_grade_report_permission(self, request: HttpRequest, object_id: Any = None) -> bool:
        return object_id is not None and bool(request.user.has_perm(Permission.GRADES_VIEW))

    @action(description=_("Grade report"), url_path="grade-report", permissions=["grade_report"], icon="description")
    def grade_report(self, request: HttpRequest, object_id: Any) -> HttpResponse:
        """The student's grade report (Phase 6, original ``ViewStudentRecord`` transcript action)."""
        record = self._record(request, object_id)
        return HttpResponseRedirect(reverse("grading:transcript", args=[record.pk]))

    @action(
        description=_("Assign advisor"), url_path="assign-advisor", permissions=["assign_advisor"], icon="person_add"
    )
    def assign_advisor(self, request: HttpRequest, object_id: Any) -> HttpResponse:
        record = self._record(request, object_id)
        form = AssignAdvisorForm(request.POST or None)
        if request.method == "POST" and form.is_valid():
            data = form.cleaned_data
            try:
                AssignAdvisor().handle(record, data["instructor"], data["start_date"], data["role"], request.user)
            except ValidationError as error:
                apply_errors(form, error)
            else:
                messages.success(request, _("Advisor assigned."))
                return HttpResponseRedirect(admin_change_url(record))
        return form_page(self, request, form, _("Assign advisor"), admin_change_url(record), subtitle=str(record))

    def get_urls(self) -> list[Any]:
        return [
            path(
                "<int:record_id>/programs/<int:program_id>/end/",
                self.admin_site.admin_view(self.end_program_view),
                name="person_studentrecord_end_program",
            ),
            *super().get_urls(),
        ]

    def end_program_view(self, request: HttpRequest, record_id: int, program_id: int) -> HttpResponse:
        record = self._record(request, record_id)
        program = get_object_or_404(StudentRecordProgram, pk=program_id, student_record=record)
        form = EndProgramForm(request.POST or None)
        if request.method == "POST" and form.is_valid():
            try:
                EndAdditionalProgram().handle(
                    program, form.cleaned_data["end_date"], form.cleaned_data["reason"], request.user
                )
            except ValidationError as error:
                apply_errors(form, error)
            else:
                messages.success(request, _("Program ended."))
                return HttpResponseRedirect(admin_change_url(record))
        title = f"{_('End')}: {program.program} ({AdditionalProgramRole(program.role).label})"
        return form_page(self, request, form, title, admin_change_url(record), subtitle=str(record))
