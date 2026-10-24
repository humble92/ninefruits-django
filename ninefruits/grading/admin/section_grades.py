"""Grade progress per section for staff (original Filament ``SectionGradeResource``): how many
grades are entered, submitted and final; finalizing submitted grades and returning them to the
instructors; the grade entry screen of a section."""

from __future__ import annotations

from typing import Any

from django.contrib import admin, messages
from django.contrib.admin.options import ActionLocation
from django.core.exceptions import PermissionDenied, ValidationError
from django.db.models import Count, Exists, OuterRef, Q
from django.http import HttpRequest, HttpResponse, HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.urls import reverse
from django.utils.translation import gettext, pgettext_lazy
from django.utils.translation import gettext_lazy as _
from unfold.decorators import action, display

from ninefruits.adminpanel.mixins import CatalogAdmin
from ninefruits.adminpanel.navigation import NavigationGroup
from ninefruits.grading.actions import FinalizeGrades
from ninefruits.grading.enums import EvaluationMethod, GradeStatus
from ninefruits.grading.models import SectionGrade
from ninefruits.organization.models import OrgUnit
from ninefruits.security.enums import Permission

from .common import ConfirmForm, DefaultTermFilter, ReasonForm, YesNoFilter, run_form

ACTIVE = ("enrolled", "completed")


def _counted(statuses: list[GradeStatus]) -> Count:
    return Count(
        "enrollments",
        filter=Q(enrollments__status__in=ACTIVE, enrollments__grade_status__in=[str(s) for s in statuses]),
    )


class OfferingUnitFilter(admin.SimpleListFilter):
    title = _("Offering unit")
    parameter_name = "unit"

    def lookups(self, request: HttpRequest, model_admin: Any) -> list[tuple[Any, Any]]:
        return [(str(unit.pk), str(unit)) for unit in OrgUnit.objects.order_by("code")]

    def queryset(self, request: HttpRequest, queryset: Any) -> Any:
        return queryset.filter(org_unit_id=self.value()) if self.value() else queryset


class ExceptionFilter(YesNoFilter):
    title = _("Submitted as an exception")
    parameter_name = "exception"

    def when_yes(self, queryset: Any) -> Any:
        return queryset.filter(grade_exception_at__isnull=False)

    def when_no(self, queryset: Any) -> Any:
        return queryset.filter(grade_exception_at__isnull=True)


def _open_grades(section_field: str = "pk") -> Any:
    from ninefruits.registration.models import Enrollment

    return Enrollment.objects.filter(
        section_id=OuterRef(section_field), status="enrolled", grade_status__in=["none", "draft"]
    )


class ReadyFilter(YesNoFilter):
    """Every registered student's grade submitted (original "Ready to finalize")."""

    title = _("Ready to finalize")
    parameter_name = "ready"

    def when_yes(self, queryset: Any) -> Any:
        from ninefruits.registration.models import Enrollment

        submitted = Enrollment.objects.filter(section_id=OuterRef("pk"), grade_status="submitted")
        return queryset.filter(Exists(submitted)).exclude(Exists(_open_grades()))

    def when_no(self, queryset: Any) -> Any:
        return queryset.filter(Exists(_open_grades()))


@admin.register(SectionGrade)
class SectionGradeAdmin(CatalogAdmin):
    navigation_group = NavigationGroup.GRADING
    navigation_icon = "edit_note"
    navigation_order = 10
    list_display = (
        "label",
        "title",
        "method_badge",
        "instructor_names",
        "pending_count",
        "submitted_count",
        "finalized_count",
        "exception_badge",
    )
    list_filter = (DefaultTermFilter, OfferingUnitFilter, ExceptionFilter, ReadyFilter)
    search_fields = ("course__code",)
    list_select_related = ("course", "version")
    ordering = ("course__code", "section_code")
    list_per_page = 50
    actions = ("finalize_selected",)
    actions_row = ("open_entry", "finalize_row", "return_row")

    # -- access ----------------------------------------------------------------------------------
    def has_view_permission(self, request: HttpRequest, obj: Any = None) -> bool:
        return bool(request.user.has_perm("view_any", SectionGrade))

    def has_add_permission(self, request: HttpRequest, *args: Any) -> bool:
        return False

    def has_change_permission(self, request: HttpRequest, obj: Any = None) -> bool:
        return False

    def has_delete_permission(self, request: HttpRequest, obj: Any = None) -> bool:
        return False

    def get_queryset(self, request: HttpRequest) -> Any:
        return (
            super()
            .get_queryset(request)
            .annotate(
                pending=_counted([GradeStatus.NONE, GradeStatus.DRAFT]),
                submitted=_counted([GradeStatus.SUBMITTED]),
                finalized=_counted([GradeStatus.FINALIZED]),
            )
            .prefetch_related("instructor_assignments__instructor__person")
        )

    def get_search_results(self, request: HttpRequest, queryset: Any, search_term: str) -> tuple[Any, bool]:
        term = search_term.strip()
        if not term:
            return queryset, False
        return queryset.filter(course__code__istartswith=term), False

    def get_actions(self, request: HttpRequest, action_location: Any = ActionLocation.CHANGE_LIST) -> dict[str, Any]:
        actions = super().get_actions(request, action_location)
        actions.pop("delete_selected", None)
        return actions

    # -- columns ---------------------------------------------------------------------------------
    @display(description=pgettext_lazy("offering", "Section"), ordering="course__code")
    def label(self, obj: SectionGrade) -> str:
        return obj.label()

    @display(description=pgettext_lazy("curriculum", "Title"))
    def title(self, obj: SectionGrade) -> str:
        return str(obj.version.title or "")

    @display(description=_("Evaluation"), label=True)
    def method_badge(self, obj: SectionGrade) -> str:
        return str(EvaluationMethod(obj.evaluation_method).label)

    @display(description=_("Instructors"))
    def instructor_names(self, obj: SectionGrade) -> str:
        names = [assignment.instructor.person.display_name() for assignment in obj.instructor_assignments.all()]
        return ", ".join(names) or "-"

    @display(description=_("Not submitted"), ordering="pending")
    def pending_count(self, obj: SectionGrade) -> int:
        return int(getattr(obj, "pending", 0))

    @display(description=pgettext_lazy("grading.fields", "Submitted"), ordering="submitted")
    def submitted_count(self, obj: SectionGrade) -> int:
        return int(getattr(obj, "submitted", 0))

    @display(description=pgettext_lazy("grading", "Final"), ordering="finalized")
    def finalized_count(self, obj: SectionGrade) -> int:
        return int(getattr(obj, "finalized", 0))

    @display(description=_("Exception"), label={str(_("Submitted as an exception")): "warning"})
    def exception_badge(self, obj: SectionGrade) -> str:
        return str(_("Submitted as an exception")) if obj.grade_exception_at is not None else "-"

    # -- actions ---------------------------------------------------------------------------------
    def _section(self, request: HttpRequest, object_id: Any) -> SectionGrade:
        return get_object_or_404(self.get_queryset(request).select_related("course", "version", "term"), pk=object_id)

    def _changelist_url(self) -> str:
        return reverse("admin:grading_sectiongrade_changelist")

    def has_open_entry_permission(self, request: HttpRequest, object_id: Any = None) -> bool:
        return self.has_view_permission(request)

    @action(
        description=pgettext_lazy("grading", "Grades"), url_path="grades", permissions=["open_entry"], icon="edit_note"
    )
    def open_entry(self, request: HttpRequest, object_id: Any) -> HttpResponse:
        section = self._section(request, object_id)
        return HttpResponseRedirect(reverse("portal:grade_entry", args=[section.pk]))

    def has_finalize_row_permission(self, request: HttpRequest, object_id: Any = None) -> bool:
        return bool(request.user.has_perm(Permission.GRADES_MANAGE))

    @action(description=_("Finalize"), url_path="finalize", permissions=["finalize_row"], icon="lock")
    def finalize_row(self, request: HttpRequest, object_id: Any) -> HttpResponse:
        section = self._section(request, object_id)
        if not section.is_in_scope_of(request.user, Permission.GRADES_MANAGE):
            raise PermissionDenied
        form = ConfirmForm(request.POST if request.method == "POST" else None)

        def perform(form: Any) -> str:
            count = FinalizeGrades().finalize(section, request.user)
            return gettext("%(count)s grade(s) finalized.") % {"count": count}

        return run_form(
            self,
            request,
            form,
            _("Finalize"),
            self._changelist_url(),
            perform,
            subtitle=f"{section.label()} {section.version.title or ''}",
            description=_(
                "Finalized grades are final: they change only through an approved grade change request. Students see "
                "them from now on."
            ),
        )

    @action(description=_("Return to instructor"), url_path="return", permissions=["finalize_row"], icon="undo")
    def return_row(self, request: HttpRequest, object_id: Any) -> HttpResponse:
        section = self._section(request, object_id)
        if not section.is_in_scope_of(request.user, Permission.GRADES_MANAGE):
            raise PermissionDenied
        form = ReasonForm(request.POST or None)

        def perform(form: Any) -> str:
            count = FinalizeGrades().return_grades(section, request.user, form.cleaned_data["reason"])
            return gettext("%(count)s grade(s) returned.") % {"count": count}

        return run_form(
            self,
            request,
            form,
            _("Return to instructor"),
            self._changelist_url(),
            perform,
            subtitle=f"{section.label()} {section.version.title or ''}",
        )

    def has_finalize_selected_permission(self, request: HttpRequest) -> bool:
        return bool(request.user.has_perm(Permission.GRADES_MANAGE))

    @action(description=_("Finalize selected"), permissions=["finalize_selected"], icon="lock")
    def finalize_selected(self, request: HttpRequest, queryset: Any) -> None:
        finalized = 0
        skipped = []
        for section in queryset.select_related("course", "term"):
            try:
                finalized += FinalizeGrades().finalize(section, request.user)
            except ValidationError, PermissionDenied:
                skipped.append(section.label())
        messages.success(request, gettext("%(count)s grade(s) finalized.") % {"count": finalized})
        if skipped:
            messages.warning(request, gettext("Not finalized: %(sections)s") % {"sections": ", ".join(skipped)})
