"""The latest stored audit per student and program (original Filament ``DegreeAuditResource``):
the graduation candidate list (legacy report_pregrade with its hard-coded 154/160 credits). Run
audits, open one, audit again, graduate the satisfied ones (bulk action)."""

from __future__ import annotations

from typing import Any

from django.contrib import admin, messages
from django.contrib.admin import helpers
from django.contrib.admin.options import ActionLocation
from django.core.exceptions import PermissionDenied
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, render
from django.urls import reverse
from django.utils.translation import gettext, pgettext_lazy
from django.utils.translation import gettext_lazy as _
from unfold.decorators import action, display

from ninefruits.adminpanel.mixins import CatalogAdmin
from ninefruits.adminpanel.navigation import NavigationGroup
from ninefruits.curriculum.enums import ProgramRole
from ninefruits.graduation.actions import GraduateStudents, RunDegreeAudits
from ninefruits.graduation.models import DegreeAudit
from ninefruits.organization.models import Program
from ninefruits.person.enums import StudentStatus
from ninefruits.person.models import Person
from ninefruits.registration.admin.common import ChoiceFilter, ConfirmForm, run_form
from ninefruits.security.enums import Permission
from ninefruits.term.models import Term

from .forms import GraduateForm, RunAuditsForm


class ProgramRoleFilter(ChoiceFilter):
    title = _("Program role")
    parameter_name = "program_role"
    choices_class = ProgramRole
    default = ProgramRole.PRIMARY.value


class SatisfiedFilter(admin.SimpleListFilter):
    title = _("Satisfied")
    parameter_name = "satisfied"

    def lookups(self, request: HttpRequest, model_admin: Any) -> list[tuple[str, Any]]:
        return [("yes", _("Satisfied")), ("no", _("Not satisfied"))]

    def queryset(self, request: HttpRequest, queryset: Any) -> Any:
        if self.value() in ("yes", "no"):
            return queryset.filter(is_satisfied=self.value() == "yes")
        return queryset


class ProgramFilter(admin.SimpleListFilter):
    title = pgettext_lazy("graduation", "Program")
    parameter_name = "program"

    def lookups(self, request: HttpRequest, model_admin: Any) -> list[tuple[str, str]]:
        return [(str(program.pk), f"{program.code} {program.name}") for program in Program.objects.order_by("code")]

    def queryset(self, request: HttpRequest, queryset: Any) -> Any:
        return queryset.filter(program_id=self.value()) if self.value() else queryset


class RecordStatusFilter(admin.SimpleListFilter):
    """The student record's status: enrolled (default) or graduated (original ``status`` filter)."""

    title = pgettext_lazy("registration", "Status")
    parameter_name = "record_status"
    default = StudentStatus.ENROLLED.value

    def lookups(self, request: HttpRequest, model_admin: Any) -> list[tuple[str, Any]]:
        return [
            ("all", _("All")),
            (StudentStatus.ENROLLED.value, StudentStatus.ENROLLED.label),
            (StudentStatus.GRADUATED.value, StudentStatus.GRADUATED.label),
        ]

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
        return queryset.filter(student_record__status=value)


def can_audit(user: Any) -> bool:
    return bool(user.has_perm(Permission.GRADUATION_AUDIT))


def can_process(user: Any) -> bool:
    return bool(user.has_perm(Permission.GRADUATION_PROCESS))


@admin.register(DegreeAudit)
class DegreeAuditAdmin(CatalogAdmin):
    navigation_group = NavigationGroup.GRADUATION
    navigation_icon = "school"
    navigation_order = 10
    list_display = (
        "student_number_column",
        "name_column",
        "program_column",
        "year_level_column",
        "record_status_column",
        "satisfied_column",
        "credits_column",
        "gpa_column",
        "audited_at",
    )
    list_filter = (ProgramRoleFilter, SatisfiedFilter, ProgramFilter, RecordStatusFilter)
    list_select_related = ("student_record__person", "program", "term")
    search_fields = ("student_record__student_number",)
    ordering = ("-audited_at", "-id")
    list_per_page = 50
    actions = ("graduate_selected",)
    actions_list = ("run_audits",)
    actions_row = ("open_row", "rerun_row")

    # -- access (original DegreeAuditPolicy) -------------------------------------------------------
    def has_view_permission(self, request: HttpRequest, obj: Any = None) -> bool:
        if obj is not None:
            return bool(request.user.has_perm("view", obj))
        return self.policy_allows(request, "view_any", DegreeAudit)

    def has_add_permission(self, request: HttpRequest, *args: Any) -> bool:
        return False

    def has_change_permission(self, request: HttpRequest, obj: Any = None) -> bool:
        return False

    def has_delete_permission(self, request: HttpRequest, obj: Any = None) -> bool:
        return False

    def get_queryset(self, request: HttpRequest) -> Any:
        return super().get_queryset(request).newest_per_student()

    def get_actions(self, request: HttpRequest, action_location: Any = ActionLocation.CHANGE_LIST) -> dict[str, Any]:
        actions = super().get_actions(request, action_location)
        actions.pop("delete_selected", None)
        return actions

    def get_search_results(self, request: HttpRequest, queryset: Any, search_term: str) -> tuple[Any, bool]:
        term = search_term.strip()
        if not term:
            return queryset, False
        people = Person.objects.search(term).values("pk")
        return (
            queryset.filter(student_record__student_number__icontains=term)
            | queryset.filter(student_record__person__in=people),
            False,
        )

    def change_view(self, request: HttpRequest, object_id: str, form_url: str = "", extra_context: Any = None) -> Any:
        """A stored audit opens as its result (the original "Open" modal)."""
        return self.open_row(request, object_id)

    # -- columns -----------------------------------------------------------------------------------
    @display(description=_("Student number"), ordering="student_record__student_number")
    def student_number_column(self, obj: DegreeAudit) -> str:
        return str(obj.student_record.student_number)

    @display(description=pgettext_lazy("people", "Name"))
    def name_column(self, obj: DegreeAudit) -> str:
        return obj.student_record.person.display_name()

    @display(description=pgettext_lazy("graduation", "Program"), header=True)
    def program_column(self, obj: DegreeAudit) -> tuple[str, str]:
        return str(obj.program.name), str(ProgramRole(obj.program_role).label)

    @display(description=pgettext_lazy("people", "Year"))
    def year_level_column(self, obj: DegreeAudit) -> Any:
        return obj.student_record.year_level

    @display(description=pgettext_lazy("registration", "Status"), label=True)
    def record_status_column(self, obj: DegreeAudit) -> str:
        return str(StudentStatus(obj.student_record.status).label)

    @display(description=_("Satisfied"), boolean=True)
    def satisfied_column(self, obj: DegreeAudit) -> bool:
        return bool(obj.is_satisfied)

    @display(description=pgettext_lazy("graduation", "Earned credits"))
    def credits_column(self, obj: DegreeAudit) -> str:
        required = f" / {obj.required_credits}" if obj.required_credits is not None else ""
        return f"{obj.earned_credits}{required}"

    @display(description=pgettext_lazy("grading", "Cumulative GPA"))
    def gpa_column(self, obj: DegreeAudit) -> str:
        return "-" if obj.cumulative_gpa is None else str(obj.cumulative_gpa)

    # -- buttons -----------------------------------------------------------------------------------
    def _changelist_url(self) -> str:
        return reverse("admin:graduation_degreeaudit_changelist")

    def _audit(self, request: HttpRequest, object_id: Any) -> DegreeAudit:
        degree_audit: DegreeAudit = get_object_or_404(
            super().get_queryset(request).select_related("student_record__person", "program", "term"), pk=object_id
        )
        return degree_audit

    def has_audit_permission(self, request: HttpRequest, object_id: Any = None) -> bool:
        return can_audit(request.user)

    def has_open_permission(self, request: HttpRequest, object_id: Any = None) -> bool:
        return self.has_view_permission(request)

    def has_process_permission(self, request: HttpRequest) -> bool:
        return can_process(request.user)

    @action(description=_("Run audits"), url_path="run", permissions=["audit"], icon="play_arrow")
    def run_audits(self, request: HttpRequest) -> HttpResponse:
        form = RunAuditsForm(request.POST or None)

        def perform(form: Any) -> str:
            data = form.cleaned_data
            term = Term.objects.filter(pk=data.get("term")).first() if data.get("term") else None
            summary = RunDegreeAudits().for_all(term, request.user, data.get("min_year_level"))
            return gettext("%(students)s student(s) audited, %(satisfied)s satisfied.") % summary

        return run_form(self, request, form, _("Run audits"), self._changelist_url(), perform)

    @action(description=pgettext_lazy("graduation", "Open"), url_path="open", permissions=["open"], icon="search")
    def open_row(self, request: HttpRequest, object_id: Any) -> HttpResponse:
        audit = self._audit(request, object_id)
        record = audit.student_record
        context = {
            **self.admin_site.each_context(request),
            "title": f"{record.student_number} {record.person.display_name()}",
            "subtitle": f"{ProgramRole(audit.program_role).label} · {audit.program.code}",
            "audit": audit,
            "opts": self.model._meta,
            "back_url": self._changelist_url(),
        }
        return render(request, "graduation/admin/audit_detail.html", context)

    @action(description=_("Audit again"), url_path="rerun", permissions=["audit"], icon="refresh")
    def rerun_row(self, request: HttpRequest, object_id: Any) -> HttpResponse:
        audit = self._audit(request, object_id)
        record = audit.student_record
        form = ConfirmForm(request.POST if request.method == "POST" else None)

        def perform(form: Any) -> str:
            RunDegreeAudits().for_record(record, request.user, audit.term)
            return gettext("Degree audit saved.")

        return run_form(
            self,
            request,
            form,
            _("Audit again"),
            self._changelist_url(),
            perform,
            subtitle=f"{record.student_number} {record.person.display_name()}",
        )

    @admin.action(description=_("Graduate"), permissions=["process"])
    def graduate_selected(self, request: HttpRequest, queryset: Any) -> HttpResponse | None:
        """Asks for the graduation date and reason, then graduates each selected student in its
        own transaction; those whose latest audit is not satisfied are reported."""
        if not can_process(request.user):
            raise PermissionDenied
        form = GraduateForm(request.POST if "apply" in request.POST else None)
        if form.is_bound and form.is_valid():
            data = form.cleaned_data
            records = [audit.student_record for audit in queryset.select_related("student_record__program")]
            summary = GraduateStudents().batch(records, data["graduation_date"], request.user, data["reason"])
            text = gettext("%(count)s student(s) graduated, %(errors)s not processed.") % {
                "count": summary["graduated"],
                "errors": len(summary["errors"]),
            }
            if summary["errors"]:
                messages.warning(request, text)
                for error in summary["errors"][:10]:
                    messages.warning(request, error)
            else:
                messages.success(request, text)
            return None
        context = {
            **self.admin_site.each_context(request),
            "title": _("Graduate"),
            "form": form,
            "opts": self.model._meta,
            "queryset": queryset.select_related("student_record__person"),
            "action_checkbox_name": helpers.ACTION_CHECKBOX_NAME,
            "back_url": self._changelist_url(),
        }
        return render(request, "graduation/admin/graduate.html", context)
