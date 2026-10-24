"""Examination sessions (original Filament ``AssessmentSessionResource`` with the
``RegistrationsRelationManager``; legacy CET_HISTORY: date and cut line only): the registration
window, the capacity, the registrants with their results, publication and CSV import.

- The session page has a **Registrants** tab: every registration with its status and result, and
  per row **Enter result** (until publication), **Request a correction** (after publication),
  **Absent** and **Cancel registration** (no result yet). **Register a student** is a button of
  the page (until the session date).
- **Publish results** and **Import results (CSV)** are row buttons of the list and buttons of the
  page.
- A changed pass score goes through ``ChangeSessionPassScore`` (results judged again, audited);
  after publication the pass score is read only."""

from __future__ import annotations

import contextvars
from typing import Any

from django.contrib import admin, messages
from django.core.exceptions import PermissionDenied, ValidationError
from django.db.models import Count, Prefetch, Q
from django.http import Http404, HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404
from django.template.loader import render_to_string
from django.urls import path, reverse
from django.utils import timezone
from django.utils.translation import gettext, pgettext, pgettext_lazy
from django.utils.translation import gettext_lazy as _
from unfold.decorators import action, display

from ninefruits.adminpanel.navigation import NavigationGroup
from ninefruits.assessment.actions import (
    ChangeSessionPassScore,
    CorrectAssessmentResult,
    RecordAssessmentResult,
    RegisterForAssessment,
)
from ninefruits.assessment.enums import AssessmentRegistrationStatus
from ninefruits.assessment.models import (
    AssessmentComponentScore,
    AssessmentRegistration,
    AssessmentResult,
    AssessmentSession,
    format_score,
)
from ninefruits.assessment.services import AssessmentResultImporter
from ninefruits.institution.admin_support import ReferenceAdmin, show_errors
from ninefruits.registration.admin.common import ConfirmForm, run_form
from ninefruits.security.enums import Permission

from .common import TypeFilter
from .forms import (
    AssessmentSessionForm,
    CancelRegistrationForm,
    CorrectionRequestForm,
    ImportResultsForm,
    ResultEntryForm,
    StudentNumberForm,
    registration_subtitle,
)

_request: contextvars.ContextVar[HttpRequest | None] = contextvars.ContextVar(
    "assessment_session_request", default=None
)

STATUS_COLORS = {
    AssessmentRegistrationStatus.REGISTERED.value: "success",
    AssessmentRegistrationStatus.ABSENT.value: "warning",
    AssessmentRegistrationStatus.CANCELLED.value: "gray",
}
OPERATIONS = ("result", "correct", "absent", "cancel")


def session_url(session_id: Any) -> str:
    return reverse("admin:assessment_assessmentsession_change", args=[session_id])


def registration_action_url(session_id: Any, registration_id: Any, operation: str) -> str:
    return reverse("admin:assessment_assessmentsession_registration", args=[session_id, registration_id, operation])


def scores_text(scores: list[AssessmentComponentScore]) -> str:
    return " · ".join(f"{score.component.code} {format_score(score.score)}" for score in scores)


def registrant_rows(
    request: HttpRequest, session: AssessmentSession, status: str | None = None
) -> list[dict[str, Any]]:
    """The registrants of a session with their results (original ``RegistrationsRelationManager``
    table) and the row actions the user may run."""
    records = bool(request.user.has_perm(Permission.ASSESSMENTS_RECORD))
    published = session.is_published
    registrations = (
        AssessmentRegistration.objects.visible_to(request.user)
        .filter(session_id=session.pk)
        .select_related("student_record__person")
        .order_by("registered_at", "id")
    )
    if status:
        registrations = registrations.filter(status=status)
    results = {
        result.registration_id: result
        for result in AssessmentResult.objects.visible_to(request.user)
        .filter(registration_id__in=[r.pk for r in registrations])
        .prefetch_related(
            Prefetch(
                "component_scores",
                queryset=AssessmentComponentScore.objects.select_related("component").order_by(
                    "component__sort_order", "id"
                ),
            )
        )
    }
    rows = []
    for registration in registrations:
        result = results.get(registration.pk)
        cancelled = registration.status == AssessmentRegistrationStatus.CANCELLED

        def url(operation: str, allowed: bool, registration: AssessmentRegistration = registration) -> str | None:
            return registration_action_url(session.pk, registration.pk, operation) if allowed else None

        rows.append(
            {
                "student_number": registration.student_record.student_number,
                "name": registration.student_record.person.display_name(),
                "status": AssessmentRegistrationStatus(registration.status).label,
                "status_value": registration.status,
                "total": format_score(result.total_score) if result is not None else None,
                "scores": scores_text(list(result.component_scores.all())) if result is not None else "",
                "has_result": result is not None,
                "passed": result.is_passed if result is not None else None,
                "registered_at": timezone.localtime(registration.registered_at),
                "result_url": url("result", records and not cancelled and not published),
                "correct_url": url("correct", records and result is not None and published),
                "absent_url": url(
                    "absent",
                    records and registration.status == AssessmentRegistrationStatus.REGISTERED and result is None,
                ),
                "cancel_url": url("cancel", records and not cancelled and result is None),
            }
        )
    return rows


class PublishedFilter(admin.SimpleListFilter):
    title = pgettext_lazy("assessment", "Results published")
    parameter_name = "published"

    def lookups(self, request: HttpRequest, model_admin: Any) -> list[tuple[Any, Any]]:
        return [("yes", _("Yes")), ("no", _("No"))]

    def queryset(self, request: HttpRequest, queryset: Any) -> Any:
        if self.value() == "yes":
            return queryset.filter(results_published_at__isnull=False)
        if self.value() == "no":
            return queryset.filter(results_published_at__isnull=True)
        return queryset


@admin.register(AssessmentSession)
class AssessmentSessionAdmin(ReferenceAdmin):
    manage_permission = Permission.ASSESSMENTS_MANAGE
    navigation_group = NavigationGroup.ASSESSMENTS
    navigation_icon = "event"
    navigation_order = 10
    translated_search_fields = ()
    form = AssessmentSessionForm
    list_display = (
        "held_date",
        "type_column",
        "venue_column",
        "closes_column",
        "registrants_column",
        "results_column",
        "published_column",
    )
    list_filter = (TypeFilter, PublishedFilter)
    list_select_related = ("assessment_type",)
    search_fields = ("assessment_type__code", "venue")
    ordering = ("-held_date", "-id")
    actions_row = ("publish_row", "import_row")
    actions_detail = ("register_student", "import_detail", "publish_detail")

    # -- list ------------------------------------------------------------------------------------
    def get_queryset(self, request: HttpRequest) -> Any:
        return (
            super()
            .get_queryset(request)
            .select_related("assessment_type")
            .annotate(
                registrant_total=Count(
                    "registrations",
                    filter=Q(registrations__status__in=AssessmentRegistrationStatus.active()),
                    distinct=True,
                ),
                result_total=Count("results", distinct=True),
            )
        )

    @display(description=pgettext_lazy("assessment", "Kind"))
    def type_column(self, obj: AssessmentSession) -> str:
        return str(obj.assessment_type.name)

    @display(description=_("Venue"))
    def venue_column(self, obj: AssessmentSession) -> str:
        return obj.venue or "-"

    @display(description=_("Registration closes"), ordering="registration_closes_at")
    def closes_column(self, obj: AssessmentSession) -> str:
        if obj.registration_closes_at is None:
            return "-"
        return timezone.localtime(obj.registration_closes_at).strftime("%Y-%m-%d %H:%M")

    @display(description=_("Registrants"), ordering="registrant_total")
    def registrants_column(self, obj: AssessmentSession) -> str:
        count = int(getattr(obj, "registrant_total", 0) or 0)
        return f"{count} / {obj.capacity}" if obj.capacity is not None else str(count)

    @display(description=pgettext_lazy("assessment", "Results"), ordering="result_total")
    def results_column(self, obj: AssessmentSession) -> int:
        return int(getattr(obj, "result_total", 0) or 0)

    @display(description=pgettext_lazy("assessment", "Results published"), ordering="results_published_at")
    def published_column(self, obj: AssessmentSession) -> str:
        if obj.results_published_at is None:
            return "-"
        return timezone.localtime(obj.results_published_at).strftime("%Y-%m-%d %H:%M")

    # -- form ------------------------------------------------------------------------------------
    def get_fieldsets(self, request: HttpRequest, obj: Any = None) -> Any:
        fields: list[Any] = [
            ("assessment_type", "held_date"),
            ("venue", "capacity"),
            ("registration_opens_at", "registration_closes_at"),
            "pass_score",
        ]
        if obj is not None and not obj.is_published:
            fields.append("pass_score_reason")
        fieldsets: list[Any] = [(None, {"fields": fields})]
        if obj is not None:
            _request.set(request)
            fieldsets.append((_("Registrants"), {"classes": ["tab"], "fields": ["registrants_table"]}))
        return fieldsets

    def get_readonly_fields(self, request: HttpRequest, obj: Any = None) -> Any:
        if obj is None:
            return ()
        readonly = ["assessment_type", "registrants_table"]
        if obj.is_published:
            readonly.append("pass_score")
        return readonly

    def save_model(self, request: HttpRequest, obj: AssessmentSession, form: Any, change: bool) -> None:
        """A changed cut line goes through the action (re-judgement, audit); the rest is a plain
        update (original ``EditAssessmentSession::handleRecordUpdate``)."""
        if not change or "pass_score" not in form.changed_data:
            super().save_model(request, obj, form, change)
            return
        new_score = obj.pass_score
        obj.pass_score = AssessmentSession.objects.values_list("pass_score", flat=True).get(pk=obj.pk)
        super().save_model(request, obj, form, change)
        try:
            summary = ChangeSessionPassScore().handle(
                obj, new_score, request.user, form.cleaned_data.get("pass_score_reason")
            )
        except ValidationError as error:
            show_errors(request, error)
            return
        obj.refresh_from_db()
        messages.success(
            request,
            gettext("%(count)s result(s) judged again: %(passed)s now passed, %(failed)s now failed.")
            % {
                "count": summary["rejudged"],
                "passed": len(summary["now_passed"]),
                "failed": len(summary["now_failed"]),
            },
        )

    @display(description="")
    def registrants_table(self, obj: AssessmentSession) -> str:
        request = _request.get()
        if request is None or obj is None or obj.pk is None:
            return ""
        status = request.GET.get("registrants") or None
        if status not in AssessmentRegistrationStatus.values:
            status = None
        statuses = [("", _("All")), *AssessmentRegistrationStatus.choices]
        return render_to_string(
            "assessment/admin/registrants.html",
            {
                "rows": registrant_rows(request, obj, status),
                "statuses": statuses,
                "current_status": status or "",
                "base_url": session_url(obj.pk),
                "colors": STATUS_COLORS,
            },
        )

    # -- buttons ---------------------------------------------------------------------------------
    def _session(self, request: HttpRequest, object_id: Any) -> AssessmentSession:
        return get_object_or_404(AssessmentSession.objects.select_related("assessment_type"), pk=object_id)

    def _records(self, request: HttpRequest) -> bool:
        return bool(request.user.has_perm(Permission.ASSESSMENTS_RECORD))

    def has_publish_results_permission(self, request: HttpRequest, object_id: Any = None) -> bool:
        if not self._records(request):
            return False
        if object_id is None:
            return True
        return AssessmentSession.objects.filter(pk=object_id, results_published_at__isnull=True).exists()

    def has_import_results_permission(self, request: HttpRequest, object_id: Any = None) -> bool:
        return self._records(request)

    def has_register_student_permission(self, request: HttpRequest, object_id: Any = None) -> bool:
        if not self._records(request):
            return False
        if object_id is None:
            return True
        return AssessmentSession.objects.filter(pk=object_id, held_date__gte=timezone.localdate()).exists()

    def _publish(self, request: HttpRequest, object_id: Any, back: str) -> HttpResponse:
        session = self._session(request, object_id)
        if not self.has_publish_results_permission(request, object_id):
            raise PermissionDenied
        form = ConfirmForm(request.POST if request.method == "POST" else None)

        def perform(form: Any) -> str:
            RecordAssessmentResult().publish(session, request.user)
            return pgettext("assessment", "Publish results")

        return run_form(
            self,
            request,
            form,
            pgettext_lazy("assessment", "Publish results"),
            back,
            perform,
            subtitle=session.label(),
            description=_("Students see their results from now on. Results entered later are visible at once."),
        )

    def _import(self, request: HttpRequest, object_id: Any, back: str) -> HttpResponse:
        session = self._session(request, object_id)
        if not self.has_import_results_permission(request, object_id):
            raise PermissionDenied
        form = ImportResultsForm(request.POST or None, request.FILES or None)

        def perform(form: Any) -> None:
            upload = form.cleaned_data["file"]
            try:
                summary = AssessmentResultImporter().import_file(session, upload.read(), request.user)
            except UnicodeDecodeError:
                raise ValidationError(_("The file is not UTF-8 text.")) from None
            text = gettext("%(recorded)s recorded, %(absent)s absent, %(errors)s error(s).") % {
                "recorded": summary.recorded,
                "absent": summary.absent,
                "errors": len(summary.errors),
            }
            if summary.errors:
                messages.warning(request, text)
                for error in summary.errors[:10]:
                    messages.warning(request, error)
            else:
                messages.success(request, text)

        return run_form(
            self,
            request,
            form,
            _("Import results (CSV)"),
            back,
            perform,
            subtitle=session.label(),
            description=_(
                "CSV with a header row: student_number, a column per area code (or total), optionally passed (Y/N), "
                "absent (Y) and note. Rows of students not registered are skipped."
            ),
            notes=[
                ", ".join(["student_number", *(c.code for c in session.assessment_type.ordered_components())])
                or "student_number, total"
            ],
        )

    @action(
        description=pgettext_lazy("assessment", "Publish results"),
        url_path="publish-results",
        permissions=["publish_results"],
        icon="campaign",
    )
    def publish_row(self, request: HttpRequest, object_id: Any) -> HttpResponse:
        return self._publish(request, object_id, reverse("admin:assessment_assessmentsession_changelist"))

    @action(
        description=_("Import results (CSV)"), url_path="import-results", permissions=["import_results"], icon="upload"
    )
    def import_row(self, request: HttpRequest, object_id: Any) -> HttpResponse:
        return self._import(request, object_id, reverse("admin:assessment_assessmentsession_changelist"))

    @action(
        description=pgettext_lazy("assessment", "Publish results"),
        url_path="publish",
        permissions=["publish_results"],
        icon="campaign",
    )
    def publish_detail(self, request: HttpRequest, object_id: Any) -> HttpResponse:
        return self._publish(request, object_id, session_url(object_id))

    @action(description=_("Import results (CSV)"), url_path="import", permissions=["import_results"], icon="upload")
    def import_detail(self, request: HttpRequest, object_id: Any) -> HttpResponse:
        return self._import(request, object_id, session_url(object_id))

    @action(
        description=pgettext_lazy("assessment", "Register a student"),
        url_path="register-student",
        permissions=["register_student"],
        icon="person_add",
    )
    def register_student(self, request: HttpRequest, object_id: Any) -> HttpResponse:
        session = self._session(request, object_id)
        if not self.has_register_student_permission(request, object_id):
            raise PermissionDenied
        form = StudentNumberForm(request.POST or None, user=request.user)

        def perform(form: Any) -> str:
            RegisterForAssessment().register(session, form.cleaned_data["student_number"], request.user, by_staff=True)
            return str(pgettext_lazy("assessment.registration_statuses", "Registered"))

        return run_form(
            self,
            request,
            form,
            pgettext_lazy("assessment", "Register a student"),
            session_url(session.pk),
            perform,
            subtitle=session.label(),
        )

    # -- registrant rows -------------------------------------------------------------------------
    def get_urls(self) -> list[Any]:
        view = self.admin_site.admin_view(self.registration_view)
        return [
            path(
                "<int:session_id>/registrations/<int:registration_id>/<str:operation>/",
                view,
                name="assessment_assessmentsession_registration",
            ),
            *super().get_urls(),
        ]

    def registration_view(
        self, request: HttpRequest, session_id: int, registration_id: int, operation: str
    ) -> HttpResponse:
        if operation not in OPERATIONS:
            raise Http404
        if not self.has_view_permission(request) or not self._records(request):
            raise PermissionDenied
        registration = get_object_or_404(
            AssessmentRegistration.objects.visible_to(request.user).select_related(
                "session__assessment_type", "student_record__person"
            ),
            pk=registration_id,
            session_id=session_id,
        )
        handler = getattr(self, f"_registration_{operation}")
        response: HttpResponse = handler(request, registration)
        return response

    def _result_of(self, request: HttpRequest, registration: AssessmentRegistration) -> AssessmentResult | None:
        return AssessmentResult.objects.visible_to(request.user).filter(registration_id=registration.pk).first()

    def _registration_result(self, request: HttpRequest, registration: AssessmentRegistration) -> HttpResponse:
        session = registration.session
        if registration.is_cancelled or session.is_published:
            raise PermissionDenied
        form = ResultEntryForm(request.POST or None, session=session, result=self._result_of(request, registration))

        def perform(form: Any) -> str:
            RecordAssessmentResult().for_registration(
                registration, form.scores(), form.passed(), request.user, form.total(), form.cleaned_data.get("note")
            )
            return gettext("Enter result")

        return run_form(
            self,
            request,
            form,
            _("Enter result"),
            session_url(session.pk),
            perform,
            subtitle=registration_subtitle(registration),
        )

    def _registration_correct(self, request: HttpRequest, registration: AssessmentRegistration) -> HttpResponse:
        session = registration.session
        result = self._result_of(request, registration)
        if result is None or not session.is_published:
            raise PermissionDenied
        form = CorrectionRequestForm(request.POST or None, session=session, result=result)

        def perform(form: Any) -> str:
            CorrectAssessmentResult().request(result, form.proposal(), form.cleaned_data["reason"], request.user)
            return gettext("Request a correction")

        return run_form(
            self,
            request,
            form,
            _("Request a correction"),
            session_url(session.pk),
            perform,
            subtitle=registration_subtitle(registration),
            description=_(
                "The results of this session are published. Propose the new values with a reason; someone else with "
                "the manage permission approves and the change is applied."
            ),
        )

    def _registration_absent(self, request: HttpRequest, registration: AssessmentRegistration) -> HttpResponse:
        form = ConfirmForm(request.POST if request.method == "POST" else None)

        def perform(form: Any) -> str:
            RegisterForAssessment().mark_absent(registration, request.user)
            return str(pgettext_lazy("assessment", "Absent"))

        return run_form(
            self,
            request,
            form,
            pgettext_lazy("assessment", "Absent"),
            session_url(registration.session_id),
            perform,
            subtitle=registration_subtitle(registration),
        )

    def _registration_cancel(self, request: HttpRequest, registration: AssessmentRegistration) -> HttpResponse:
        form = CancelRegistrationForm(request.POST if request.method == "POST" else None)

        def perform(form: Any) -> str:
            RegisterForAssessment().cancel(registration, request.user, form.cleaned_data.get("reason"))
            return gettext("Cancel registration")

        return run_form(
            self,
            request,
            form,
            _("Cancel registration"),
            session_url(registration.session_id),
            perform,
            subtitle=registration_subtitle(registration),
        )
