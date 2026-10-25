"""Applications for staff (original Filament ``ApplicationResource`` and ``ViewApplication``):
review, decide, release decisions and matriculate. Applicants create and submit applications in
the portal; staff never edit their answers. Drafts are the applicant's private work and are not
listed."""

from __future__ import annotations

from typing import Any, ClassVar

from django import forms
from django.contrib import admin, messages
from django.contrib.admin import helpers
from django.core.exceptions import PermissionDenied, ValidationError
from django.db.models import QuerySet
from django.http import HttpRequest, HttpResponse, HttpResponseRedirect
from django.shortcuts import get_object_or_404, render
from django.urls import reverse
from django.utils.html import format_html, format_html_join
from django.utils.safestring import mark_safe
from django.utils.translation import gettext_lazy as _
from django.utils.translation import pgettext_lazy
from unfold.contrib.filters.admin import ChoicesDropdownFilter, RelatedDropdownFilter
from unfold.decorators import action, display
from unfold.enums import ActionVariant
from unfold.forms import BaseDialogForm
from unfold.widgets import UnfoldAdminRadioSelectWidget, UnfoldAdminSelectWidget, UnfoldAdminTextareaWidget

from ninefruits.adminpanel.mixins import ReadOnlyCatalogAdmin
from ninefruits.adminpanel.navigation import NavigationGroup
from ninefruits.admission.actions import DecideApplication, MatriculateApplicant, ReleaseDecisions, RespondToOffer
from ninefruits.admission.enums import ApplicationStatus
from ninefruits.admission.models import Application
from ninefruits.institution.models import LookupValue
from ninefruits.person.models import Person, StudentRecord
from ninefruits.security.enums import Permission
from ninefruits.term.enums import TermStatus
from ninefruits.term.models import Term

from .cycles import RELEASE_HELP, ReleaseDecisionsForm, released_message

_BADGES = {
    str(ApplicationStatus.SUBMITTED.label): "warning",
    str(ApplicationStatus.UNDER_REVIEW.label): "warning",
    str(ApplicationStatus.ADMITTED.label): "success",
    str(ApplicationStatus.CONFIRMED.label): "success",
    str(ApplicationStatus.REJECTED.label): "danger",
}


def _admission_terms() -> QuerySet[Term]:
    return Term.objects.filter(status__in=[TermStatus.PLANNED, TermStatus.PUBLISHED]).order_by("start_date")


class AdmissionTermField(forms.ModelChoiceField):  # type: ignore[type-arg]
    def __init__(self, **kwargs: Any) -> None:
        super().__init__(
            queryset=_admission_terms(),
            label=_("Admission term"),
            help_text=_("The term the new students start in. Their admission date is the term's first day."),
            widget=UnfoldAdminSelectWidget,
            **kwargs,
        )

    def label_from_instance(self, obj: Term) -> str:
        return f"{obj.name} ({obj.start_date.isoformat()})"


def _note(required: bool) -> forms.CharField:
    return forms.CharField(
        label=pgettext_lazy("admissions", "Decision note"),
        required=required,
        max_length=2000,
        widget=UnfoldAdminTextareaWidget(attrs={"rows": 3}),
    )


class AdmitForm(BaseDialogForm):
    note = _note(required=False)


class RejectForm(BaseDialogForm):
    note = _note(required=True)


class MatriculateForm(BaseDialogForm):
    admission_term = AdmissionTermField()


class RecordResponseForm(BaseDialogForm):
    response = forms.ChoiceField(
        label=_("Response"),
        choices=[("accept", _("Accept the offer")), ("decline", _("Decline"))],
        widget=UnfoldAdminRadioSelectWidget,
    )
    reason = forms.CharField(
        label=pgettext_lazy("common", "Reason"), max_length=1000, widget=UnfoldAdminTextareaWidget(attrs={"rows": 3})
    )


class BulkMatriculateForm(forms.Form):
    admission_term = AdmissionTermField()


@admin.register(Application)
class ApplicationAdmin(ReadOnlyCatalogAdmin):
    permissions: ClassVar[dict[str, str]] = {"view": Permission.APPLICATIONS_VIEW}
    navigation_group = NavigationGroup.ADMISSIONS
    navigation_icon = "description"
    navigation_order = 20
    list_display = (
        "application_number",
        "applicant_name",
        "program_name",
        "cycle_name",
        "status_badge",
        "released",
        "submitted_at",
    )
    list_filter = (("admission_cycle", RelatedDropdownFilter), ("status", ChoicesDropdownFilter))
    list_filter_submit = True
    list_select_related = ("person", "program", "admission_cycle")
    ordering = ("submitted_at", "id")
    show_full_result_count = False
    actions = ("release_selected", "matriculate_selected")
    actions_detail = ("start_review", "admit", "reject", "release", "matriculate", "record_response")
    readonly_fields = (
        "application_number",
        "status_badge",
        "cycle_name",
        "program_name",
        "admission_type_name",
        "submitted_at",
        "previous_school_name",
        "previous_school_country_name",
        "previous_graduation_date",
        "personal_statement",
        "applicant_link",
        "applicant_birth_date",
        "applicant_email",
        "applicant_phone",
        "earlier_records",
        "documents",
        "decided_by_email",
        "decided_at",
        "decision_note",
        "released",
        "offer_expires_at",
        "student_number",
    )
    fieldsets = (
        (
            _("Application"),
            {
                "fields": (
                    ("application_number", "status_badge"),
                    ("cycle_name", "program_name"),
                    ("admission_type_name", "submitted_at"),
                    ("previous_school_name", "previous_school_country_name"),
                    "previous_graduation_date",
                    "personal_statement",
                )
            },
        ),
        (
            _("Applicant"),
            {
                "fields": (
                    ("applicant_link", "applicant_birth_date"),
                    ("applicant_email", "applicant_phone"),
                    "earlier_records",
                    "documents",
                )
            },
        ),
        (
            _("Decision"),
            {
                "fields": (
                    ("decided_by_email", "decided_at"),
                    "decision_note",
                    ("released", "offer_expires_at"),
                    "student_number",
                )
            },
        ),
    )

    # -- permissions (original ApplicationPolicy) -------------------------------------------------
    def has_view_permission(self, request: HttpRequest, obj: Any = None) -> bool:
        if obj is not None:
            return bool(request.user.has_perm("view", obj))
        return self.policy_allows(request, "view_any", Application)

    def get_queryset(self, request: HttpRequest) -> Any:
        return super().get_queryset(request).exclude(status=ApplicationStatus.DRAFT)

    # -- list -------------------------------------------------------------------------------------
    def get_search_fields(self, request: HttpRequest) -> tuple[str, ...]:
        return ("application_number",)

    def get_search_results(self, request: HttpRequest, queryset: Any, search_term: str) -> tuple[Any, bool]:
        term = search_term.strip()
        if not term:
            return queryset, False
        people = Person.objects.search(term).values("pk")
        return queryset.filter(application_number__icontains=term) | queryset.filter(person__in=people), False

    @display(description=pgettext_lazy("people", "Name"))
    def applicant_name(self, obj: Application) -> str:
        return obj.person.display_name()

    @display(description=pgettext_lazy("security", "Program"))
    def program_name(self, obj: Application) -> str:
        return str(obj.program.name)

    @display(description=_("Admission cycle"))
    def cycle_name(self, obj: Application) -> str:
        return str(obj.admission_cycle.name)

    @display(description=pgettext_lazy("admissions", "Status"), label=_BADGES)
    def status_badge(self, obj: Application) -> str:
        return str(obj.application_status.label)

    @display(description=pgettext_lazy("admissions", "Released"), boolean=True)
    def released(self, obj: Application) -> bool:
        return obj.decision_released_at is not None

    # -- detail -------------------------------------------------------------------------------------
    @display(description=_("Admission type"))
    def admission_type_name(self, obj: Application) -> str:
        return str(obj.admission_type.name) if obj.admission_type else "-"

    @display(description=_("Country of previous school"))
    def previous_school_country_name(self, obj: Application) -> str:
        return str(obj.previous_school_country.name) if obj.previous_school_country else "-"

    @display(description=pgettext_lazy("people", "Name"))
    def applicant_link(self, obj: Application) -> Any:
        person = obj.person
        label = f"{person.display_name()} ({person.romanized_name()})"
        request = getattr(self, "_request", None)
        if request is not None and request.user.has_perm("view", person):
            url = reverse("admin:person_person_change", args=[person.pk])
            return format_html('<a class="underline" href="{}">{}</a>', url, label)
        return label

    @display(description=_("Birth date"))
    def applicant_birth_date(self, obj: Application) -> Any:
        return obj.person.birth_date or "-"

    @display(description=_("Contact email"))
    def applicant_email(self, obj: Application) -> str:
        return obj.person.email or "-"

    @display(description=_("Phone"))
    def applicant_phone(self, obj: Application) -> str:
        return obj.person.phone or "-"

    @display(description=_("Earlier student records"))
    def earlier_records(self, obj: Application) -> str:
        numbers = list(
            StudentRecord.objects.filter(person_id=obj.person_id)
            .order_by("admission_date")
            .values_list("student_number", flat=True)
        )
        return ", ".join(numbers) or str(pgettext_lazy("common", "None"))

    @display(description=_("Documents"))
    def documents(self, obj: Application) -> Any:
        """Download links of the uploaded documents, labelled with their document type."""
        files = list(obj.get_media(Application.DOCUMENTS_COLLECTION))
        if not files:
            return str(pgettext_lazy("common", "None"))
        type_ids = {media.custom_property("document_type_id") for media in files}
        names = {value.pk: str(value.name) for value in LookupValue.objects.filter(pk__in=[t for t in type_ids if t])}
        return format_html_join(
            mark_safe("<br>"),  # a constant separator  # nosec B308
            '{}: <a href="{}" class="underline">{}</a>',
            (
                (
                    names.get(_as_int(media.custom_property("document_type_id")), "-"),
                    reverse("admission:document", args=[obj.pk, media.pk]),
                    media.file_name,
                )
                for media in files
            ),
        )

    @display(description=pgettext_lazy("admissions", "Decided by"))
    def decided_by_email(self, obj: Application) -> str:
        return obj.decided_by.email if obj.decided_by else "-"

    @display(description=_("Student number"))
    def student_number(self, obj: Application) -> str:
        return obj.student_record.student_number if obj.student_record else "-"

    def change_view(self, request: HttpRequest, object_id: str, form_url: str = "", extra_context: Any = None) -> Any:
        self._request = request
        return super().change_view(request, object_id, form_url, extra_context)

    # -- detail actions (original ViewApplication header actions) ----------------------------------
    def _application(self, request: HttpRequest, object_id: Any) -> Application:
        application: Application = get_object_or_404(
            Application.objects.visible_to(request.user)
            .exclude(status=ApplicationStatus.DRAFT)
            .select_related("admission_cycle", "person", "program"),
            pk=object_id,
        )
        return application

    def _find(self, request: HttpRequest, object_id: Any) -> Application | None:
        if object_id is None:
            return None
        return Application.objects.visible_to(request.user).filter(pk=object_id).first()

    def has_start_review_permission(self, request: HttpRequest, object_id: Any = None) -> bool:
        application = self._find(request, object_id)
        return (
            application is not None
            and request.user.has_perm("review", application)
            and application.status == ApplicationStatus.SUBMITTED
        )

    def has_decide_permission(self, request: HttpRequest, object_id: Any = None) -> bool:
        application = self._find(request, object_id)
        return (
            application is not None
            and request.user.has_perm("review", application)
            and application.is_decision_changeable()
        )

    def has_release_permission(self, request: HttpRequest, object_id: Any = None) -> bool:
        application = self._find(request, object_id)
        return (
            application is not None
            and request.user.has_perm("review", application)
            and application.application_status.is_decided()
            and not application.is_decision_visible_to_applicant()
        )

    def has_matriculate_permission(self, request: HttpRequest, object_id: Any = None) -> bool:
        application = self._find(request, object_id)
        return (
            application is not None
            and request.user.has_perm("matriculate", application)
            and application.status == ApplicationStatus.CONFIRMED
            and application.student_record_id is None
        )

    def has_record_response_permission(self, request: HttpRequest, object_id: Any = None) -> bool:
        application = self._find(request, object_id)
        return (
            application is not None
            and request.user.has_perm("review", application)
            and application.status == ApplicationStatus.ADMITTED
            and application.is_decision_visible_to_applicant()
        )

    def _back(self, application: Application) -> HttpResponse:
        return HttpResponseRedirect(reverse("admin:admission_application_change", args=[application.pk]))

    def _run(self, request: HttpRequest, application: Application, callback: Any, success: Any) -> HttpResponse:
        try:
            callback()
        except PermissionDenied:
            raise
        except ValidationError as error:
            for message in error.messages:
                messages.error(request, message)
        else:
            if success:
                messages.success(request, success)
        return self._back(application)

    @action(
        description=_("Start review"),
        url_path="start-review",
        permissions=["start_review"],
        icon="visibility",
        dialog={"title": _("Start review"), "form_class": ReleaseDecisionsForm},
    )
    def start_review(self, request: HttpRequest, form: Any, object_id: Any) -> HttpResponse:
        application = self._application(request, object_id)
        return self._run(
            request, application, lambda: DecideApplication().start_review(application, request.user), None
        )

    @action(
        description=_("Admit"),
        url_path="admit",
        permissions=["decide"],
        icon="check",
        variant=ActionVariant.SUCCESS,
        dialog={"title": _("Admit"), "form_class": AdmitForm},
    )
    def admit(self, request: HttpRequest, form: AdmitForm, object_id: Any) -> HttpResponse:
        application = self._application(request, object_id)
        note = form.cleaned_data.get("note") or None
        return self._run(
            request,
            application,
            lambda: DecideApplication().admit(application, request.user, note),
            _("Decision saved. The applicant sees it once it is released."),
        )

    @action(
        description=pgettext_lazy("admissions", "Reject"),
        url_path="reject",
        permissions=["decide"],
        icon="close",
        variant=ActionVariant.DANGER,
        dialog={"title": pgettext_lazy("admissions", "Reject"), "form_class": RejectForm},
    )
    def reject(self, request: HttpRequest, form: RejectForm, object_id: Any) -> HttpResponse:
        application = self._application(request, object_id)
        note = form.cleaned_data["note"]
        return self._run(
            request,
            application,
            lambda: DecideApplication().reject(application, request.user, note),
            _("Decision saved. The applicant sees it once it is released."),
        )

    @action(
        description=_("Release decision"),
        url_path="release",
        permissions=["release"],
        icon="campaign",
        dialog={"title": _("Release decision"), "description": RELEASE_HELP, "form_class": ReleaseDecisionsForm},
    )
    def release(self, request: HttpRequest, form: Any, object_id: Any) -> HttpResponse:
        application = self._application(request, object_id)
        count = ReleaseDecisions().handle([application], request.user)
        messages.success(request, released_message(count))
        return self._back(application)

    @action(
        description=_("Create student record"),
        url_path="matriculate",
        permissions=["matriculate"],
        icon="school",
        variant=ActionVariant.SUCCESS,
        dialog={"title": _("Create student record"), "form_class": MatriculateForm},
    )
    def matriculate(self, request: HttpRequest, form: MatriculateForm, object_id: Any) -> HttpResponse:
        application = self._application(request, object_id)
        try:
            record = MatriculateApplicant().handle(application, form.cleaned_data["admission_term"], request.user)
        except ValidationError as error:
            for message in error.messages:
                messages.error(request, message)
            return self._back(application)
        messages.success(request, _("Student record %(number)s created.") % {"number": record.student_number})
        if record.is_visible_to(request.user):
            return HttpResponseRedirect(reverse("admin:person_studentrecord_change", args=[record.pk]))
        return self._back(application)

    @action(
        description=_("Record offer response"),
        url_path="record-response",
        permissions=["record_response"],
        icon="edit_note",
        dialog={"title": _("Record offer response"), "form_class": RecordResponseForm},
    )
    def record_response(self, request: HttpRequest, form: RecordResponseForm, object_id: Any) -> HttpResponse:
        application = self._application(request, object_id)
        data = form.cleaned_data
        return self._run(
            request,
            application,
            lambda: RespondToOffer().handle(application, data["response"] == "accept", request.user, data["reason"]),
            None,
        )

    # -- bulk actions (original table toolbar actions) ---------------------------------------------
    def has_review_any_permission(self, request: HttpRequest) -> bool:
        return bool(request.user.has_perm(Permission.APPLICATIONS_REVIEW))

    def has_matriculate_any_permission(self, request: HttpRequest) -> bool:
        return bool(request.user.has_perm(Permission.APPLICATIONS_MATRICULATE))

    @admin.action(description=_("Release decisions"), permissions=["review_any"])
    def release_selected(self, request: HttpRequest, queryset: QuerySet[Application]) -> None:
        applications = queryset.select_related("admission_cycle", "person", "program")
        messages.success(request, released_message(ReleaseDecisions().handle(applications, request.user)))

    @admin.action(description=_("Create student record"), permissions=["matriculate_any"])
    def matriculate_selected(self, request: HttpRequest, queryset: QuerySet[Application]) -> HttpResponse | None:
        """Asks for the admission term, then matriculates each selected application in its own
        transaction; applications that are not ready or outside the scope are skipped."""
        form = BulkMatriculateForm(request.POST if "apply" in request.POST else None)
        if form.is_bound and form.is_valid():
            term = form.cleaned_data["admission_term"]
            matriculate = MatriculateApplicant()
            done = skipped = 0
            for application in queryset.select_related("admission_cycle", "person", "program"):
                try:
                    matriculate.handle(application, term, request.user)
                except ValidationError, PermissionDenied:
                    skipped += 1
                else:
                    done += 1
            messages.success(
                request,
                _("%(count)s student record(s) created, %(skipped)s skipped.") % {"count": done, "skipped": skipped},
            )
            return None
        context = {
            **self.admin_site.each_context(request),
            "title": _("Create student record"),
            "form": form,
            "opts": self.model._meta,
            "queryset": queryset,
            "action_checkbox_name": helpers.ACTION_CHECKBOX_NAME,
            "back_url": reverse("admin:admission_application_changelist"),
        }
        return render(request, "admission/admin/matriculate.html", context)


def _as_int(value: Any) -> int | None:
    try:
        return int(value)
    except TypeError, ValueError:
        return None
