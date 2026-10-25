"""Term records (original Filament ``TermRecordResource`` and ``ListTermRecords``): credits, GPA,
academic standing and honors per student and term (legacy report_warn*, report_toplevel*
reports). Term close (with a dry run first) and recalculation start here; a running term close
shows its progress (``job_batches``)."""

from __future__ import annotations

from typing import Any

from django.contrib import admin, messages
from django.contrib.admin.options import ActionLocation
from django.core.exceptions import ValidationError
from django.http import HttpRequest, HttpResponse, HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.urls import reverse
from django.utils.translation import gettext, pgettext_lazy
from django.utils.translation import gettext_lazy as _
from unfold.decorators import action, display

from ninefruits.adminpanel.mixins import CatalogAdmin
from ninefruits.adminpanel.navigation import NavigationGroup
from ninefruits.core.batches import JobBatch
from ninefruits.grading.actions import CloseTerm, RecalculateTermRecords
from ninefruits.grading.actions.close_term import BATCH_PREFIX
from ninefruits.grading.enums import AcademicStanding
from ninefruits.grading.models import TermRecord
from ninefruits.institution.admin_support import render_action_form, show_errors
from ninefruits.organization.models import Program
from ninefruits.person.models import Person
from ninefruits.security.enums import Permission
from ninefruits.term.models import Term

from .common import ChoiceFilter, CloseTermForm, DefaultTermFilter, RecalculateForm, YesNoFilter, run_form

STANDING_COLORS = {
    AcademicStanding.WARNING.label: "warning",
    AcademicStanding.DISMISSAL_REVIEW.label: "danger",
}


class RecordTermFilter(DefaultTermFilter):
    """The latest term with term records by default."""

    def value(self) -> Any:
        value = super(DefaultTermFilter, self).value()
        if value is None:
            latest = (
                TermRecord.objects.order_by("-term__start_date").values_list("term_id", flat=True).first()
                or super().value()
            )
            return str(latest) if latest is not None else None
        return value


class StandingFilter(ChoiceFilter):
    title = _("Academic standing")
    parameter_name = "academic_standing"
    choices_class = AcademicStanding


class HonorsFilter(YesNoFilter):
    title = pgettext_lazy("grading", "Honors")
    parameter_name = "honors"

    def when_yes(self, queryset: Any) -> Any:
        return queryset.filter(is_honors=True)

    def when_no(self, queryset: Any) -> Any:
        return queryset.filter(is_honors=False)


class ProgramFilter(admin.SimpleListFilter):
    title = _("program")
    parameter_name = "program"

    def lookups(self, request: HttpRequest, model_admin: Any) -> list[tuple[Any, Any]]:
        return [(str(program.pk), f"{program.code} {program.name}") for program in Program.objects.order_by("code")]

    def queryset(self, request: HttpRequest, queryset: Any) -> Any:
        return queryset.filter(student_record__program_id=self.value()) if self.value() else queryset


@admin.register(TermRecord)
class TermRecordAdmin(CatalogAdmin):
    navigation_group = NavigationGroup.GRADING
    navigation_icon = "bar_chart"
    navigation_order = 30
    list_display = (
        "student_number",
        "name",
        "program_name",
        "term_name",
        "term_gpa",
        "credits",
        "cumulative_gpa",
        "standing_badge",
        "warning_count",
        "honors_rank",
        "closed",
    )
    list_filter = (RecordTermFilter, StandingFilter, HonorsFilter, ProgramFilter)
    search_fields = ("student_record__student_number",)
    list_select_related = ("student_record__person", "student_record__program", "term")
    ordering = ("-term_gpa", "student_record__student_number")
    list_per_page = 50
    actions_list = ("close_term", "recalculate")
    actions_row = ("transcript_row",)
    list_before_template = "grading/admin/term_close_progress.html"

    # -- access ----------------------------------------------------------------------------------
    def has_view_permission(self, request: HttpRequest, obj: Any = None) -> bool:
        return self.policy_allows(request, "view_any", TermRecord)

    def has_add_permission(self, request: HttpRequest, *args: Any) -> bool:
        return False

    def has_change_permission(self, request: HttpRequest, obj: Any = None) -> bool:
        return False

    def has_delete_permission(self, request: HttpRequest, obj: Any = None) -> bool:
        return False

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

    def changelist_view(self, request: HttpRequest, extra_context: dict[str, Any] | None = None) -> Any:
        batches = []
        for batch in JobBatch.objects.named(BATCH_PREFIX).order_by("-created_at")[:3]:
            batches.append(
                {
                    "term": batch.name.removeprefix(BATCH_PREFIX),
                    "progress": batch.progress(),
                    "processed": batch.processed(),
                    "total": batch.total_jobs,
                    "finished": batch.is_finished,
                    "failed": batch.has_failures,
                }
            )
        running = [batch for batch in batches if not batch["finished"]]
        return super().changelist_view(request, {**(extra_context or {}), "term_close_batches": running})

    # -- columns ---------------------------------------------------------------------------------
    @display(description=_("Student number"), ordering="student_record__student_number")
    def student_number(self, obj: TermRecord) -> str:
        return str(obj.student_record.student_number)

    @display(description=pgettext_lazy("people", "Name"))
    def name(self, obj: TermRecord) -> str:
        return str(obj.student_record.person.display_name())

    @display(description=_("program"))
    def program_name(self, obj: TermRecord) -> str:
        return str(obj.student_record.program.name)

    @display(description=_("term"))
    def term_name(self, obj: TermRecord) -> str:
        return str(obj.term.name)

    @display(description=pgettext_lazy("grading", "Earned credits"))
    def credits(self, obj: TermRecord) -> str:
        return f"{obj.earned_credits.normalize():f} / {obj.attempted_credits.normalize():f}"

    @display(description=_("Academic standing"), label=STANDING_COLORS)
    def standing_badge(self, obj: TermRecord) -> str:
        return str(AcademicStanding(obj.academic_standing).label) if obj.academic_standing else "-"

    @display(description=pgettext_lazy("grading", "Closed"), boolean=True)
    def closed(self, obj: TermRecord) -> bool:
        return obj.closed_at is not None

    # -- actions ---------------------------------------------------------------------------------
    def _changelist_url(self) -> str:
        return reverse("admin:grading_termrecord_changelist")

    def has_transcript_row_permission(self, request: HttpRequest, object_id: Any = None) -> bool:
        return bool(request.user.has_perm(Permission.GRADES_VIEW))

    @action(description=_("Grade report"), url_path="transcript", permissions=["transcript_row"], icon="description")
    def transcript_row(self, request: HttpRequest, object_id: Any) -> HttpResponse:
        record = get_object_or_404(self.get_queryset(request), pk=object_id)
        return HttpResponseRedirect(reverse("grading:transcript", args=[record.student_record_id]))

    def has_close_term_permission(self, request: HttpRequest) -> bool:
        return bool(request.user.has_perm(Permission.GRADES_MANAGE))

    @action(description=_("Close term"), url_path="close-term", permissions=["close_term"], icon="lock")
    def close_term(self, request: HttpRequest) -> HttpResponse:
        form = CloseTermForm(request.POST or None)
        description = _(
            "Every grade of the term must be final. Closing calculates term records, academic standing and honors, "
            "and moves the term to grades closed."
        )
        if request.method == "POST" and form.is_valid():
            term = get_object_or_404(Term.objects.select_related("term_type"), pk=form.cleaned_data["term_id"])
            close = CloseTerm()
            preflight = close.preflight(term)
            if form.cleaned_data.get("dry_run") or not preflight.is_ready():
                if preflight.is_ready():
                    messages.success(
                        request, gettext("Ready to close: %(students)s student(s).") % {"students": preflight.students}
                    )
                else:
                    messages.warning(
                        request,
                        gettext("Cannot close yet: %(sections)s section(s) have grades that are not final.")
                        % {"sections": len(preflight.open_sections)},
                    )
                    for entry in preflight.open_sections[:30]:
                        messages.warning(
                            request,
                            gettext("%(section)s: %(count)s not final")
                            % {"section": entry.section.label(), "count": entry.unfinished_count},
                        )
                return render_action_form(
                    self, request, form, _("Close term"), self._changelist_url(), description=description
                )
            try:
                close.close(term, request.user, form.cleaned_data.get("reason"))
            except ValidationError as error:
                show_errors(request, error)
                return render_action_form(
                    self, request, form, _("Close term"), self._changelist_url(), description=description
                )
            messages.success(request, gettext("Term close started. The term moves to grades closed when it finishes."))
            return HttpResponseRedirect(self._changelist_url() + f"?term={term.pk}")
        return render_action_form(self, request, form, _("Close term"), self._changelist_url(), description=description)

    def has_recalculate_permission(self, request: HttpRequest) -> bool:
        return bool(request.user.has_perm(Permission.GRADES_MANAGE))

    @action(description=_("Recalculate"), url_path="recalculate", permissions=["recalculate"], icon="refresh")
    def recalculate(self, request: HttpRequest) -> HttpResponse:
        form = RecalculateForm(request.POST or None)

        def perform(form: Any) -> str:
            term = get_object_or_404(Term, pk=form.cleaned_data["term_id"])
            count = RecalculateTermRecords().handle(term, None, form.cleaned_data["reason"], request.user)
            return gettext("%(count)s student(s) recalculated.") % {"count": count}

        return run_form(
            self,
            request,
            form,
            _("Recalculate"),
            self._changelist_url(),
            perform,
            description=_(
                "Recalculates credits and GPA from final grades, e.g. after a policy change. Standing and honors stay "
                "as decided at term close."
            ),
        )
