"""Portal pages of applicants (original Livewire ``Applications`` and ``ApplicationDetail``),
mounted in the ``portal`` namespace.

The same pages serve new applicants, students and graduates applying again. Applying needs a
verified personal email (original ``verified`` middleware, porting-plan 7.1). Under row level
security an applicant only reaches their own applications; others are a 404."""

from __future__ import annotations

from typing import Any

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied, ValidationError
from django.db.models import Prefetch
from django.http import Http404, HttpRequest, HttpResponse, HttpResponseBadRequest, HttpResponseRedirect
from django.shortcuts import get_object_or_404, render
from django.urls import path, reverse
from django.utils.translation import gettext as _
from django.utils.translation import pgettext_lazy
from django.views import View

from ninefruits.admission.actions import (
    AttachApplicationDocument,
    RespondToOffer,
    StartApplication,
    SubmitApplication,
    UpdateApplicantPersonalDetails,
    UpdateApplication,
    WithdrawApplication,
    can_edit_identity,
)
from ninefruits.admission.enums import ApplicationStatus
from ninefruits.admission.models import (
    AdmissionCycle,
    AdmissionCycleDocumentType,
    AdmissionCycleProgram,
    Application,
)
from ninefruits.institution.models import Country
from ninefruits.organization.models import Program
from ninefruits.person.enums import Gender
from ninefruits.person.models import Person


def _redirect(request: HttpRequest, url: str) -> HttpResponse:
    """A redirect; HTMX requests get ``HX-Redirect`` so the whole page changes."""
    if request.headers.get("HX-Request"):
        response = HttpResponse(status=204)
        response["HX-Redirect"] = url
        return response
    return HttpResponseRedirect(url)


def _invalid_status(request: HttpRequest) -> int:
    """HTMX swaps only successful responses: form errors come back as 200 for it."""
    return 200 if request.headers.get("HX-Request") else 422


def _flash_errors(request: HttpRequest, error: ValidationError) -> None:
    for message in error.messages:
        messages.error(request, message)


def _errors_by_field(error: ValidationError) -> dict[str, list[str]]:
    if hasattr(error, "error_dict"):
        return {
            ("general" if field == "__all__" else field): [str(message) for message in messages_]
            for field, messages_ in error.message_dict.items()
        }
    return {"general": [str(message) for message in error.messages]}


def _accepting_cycles() -> list[AdmissionCycle]:
    return list(
        AdmissionCycle.objects.accepting_applications()
        .prefetch_related(
            Prefetch("programs", queryset=AdmissionCycleProgram.objects.select_related("program").order_by("id"))
        )
        .order_by("opens_at")
    )


class ApplicantMixin(LoginRequiredMixin):
    """Signed-in account with a person and a verified email."""

    def dispatch(self, request: HttpRequest, *args: Any, **kwargs: Any) -> Any:
        if not request.user.is_authenticated:
            return self.handle_no_permission()
        if request.user.person_id is None:
            raise Http404
        if not request.user.has_verified_email():
            return HttpResponseRedirect(reverse("admission:verify_email"))
        return super().dispatch(request, *args, **kwargs)


class ApplicationsView(ApplicantMixin, View):
    """The applicant's applications and the cycles open for a new one."""

    template_name = "admission/portal/applications.html"

    def get(self, request: HttpRequest) -> HttpResponse:
        return self.render(request)

    def render(self, request: HttpRequest, errors: dict[str, list[str]] | None = None, status: int = 200) -> Any:
        cycles = _accepting_cycles()
        selected = _int(request.POST.get("cycle") or request.GET.get("cycle"))
        if selected is None and len(cycles) == 1:
            selected = cycles[0].pk
        cycle = next((cycle for cycle in cycles if cycle.pk == selected), None)
        applications = [
            {"application": application, "status": application.applicant_status()}
            for application in Application.objects.filter(person_id=request.user.person_id)
            .select_related("admission_cycle", "program")
            .order_by("-created_at", "-id")
        ]
        return render(
            request,
            self.template_name,
            {
                "title": _("My applications"),
                "applications": applications,
                "cycles": cycles,
                "selected_cycle": cycle,
                "programs": sorted(cycle.programs.all(), key=lambda offered: str(offered.program.name))
                if cycle
                else [],
                "selected_program": _int(request.POST.get("program")),
                "errors": errors or {},
            },
            status=status,
        )

    def post(self, request: HttpRequest) -> HttpResponse:
        cycle = AdmissionCycle.objects.filter(pk=_int(request.POST.get("cycle")) or 0).first()
        program = Program.objects.filter(pk=_int(request.POST.get("program")) or 0).first()
        errors: dict[str, list[str]] = {}
        if cycle is None:
            errors["admission_cycle_id"] = [_("This field is required.")]
        if program is None:
            errors["program_id"] = [_("This field is required.")]
        if errors:
            return self.render(request, errors, status=422)
        try:
            application = StartApplication().handle(request.user, cycle, program)  # type: ignore[arg-type]
        except ValidationError as error:
            return self.render(request, _errors_by_field(error), status=422)
        return HttpResponseRedirect(reverse("portal:application", args=[application.pk]))


class ApplicationDetailView(ApplicantMixin, View):
    """One application: the form while it is a draft, then its status, the released decision and
    the offer response."""

    template_name = "admission/portal/application_detail.html"
    actions = frozenset({"save", "submit", "respond", "withdraw"})

    def _application(self, request: HttpRequest, pk: int) -> Application:
        return get_object_or_404(
            Application.objects.filter(person_id=request.user.person_id).select_related(
                "admission_cycle", "program", "student_record", "person"
            ),
            pk=pk,
        )

    def get(self, request: HttpRequest, pk: int) -> HttpResponse:
        return self.render(request, self._application(request, pk))

    def render(
        self,
        request: HttpRequest,
        application: Application,
        errors: dict[str, list[str]] | None = None,
        data: dict[str, Any] | None = None,
        status: int = 200,
    ) -> HttpResponse:
        person: Person = application.person
        cycle = application.admission_cycle
        documents: dict[int, list[Any]] = {}
        for media in application.get_media(Application.DOCUMENTS_COLLECTION):
            type_id = _int(media.custom_property("document_type_id"))
            if type_id is not None:
                documents.setdefault(type_id, []).append(media)
        document_types = [
            {
                "type": required,
                "files": documents.get(required.document_type_id, []),
                "errors": (errors or {}).get(f"uploads.{required.document_type_id}", []),
            }
            for required in AdmissionCycleDocumentType.objects.filter(admission_cycle=cycle)
            .select_related("document_type")
            .order_by("id")
        ]
        values = {
            "program_id": application.program_id,
            "admission_type_id": application.admission_type_id,
            "previous_school_name": application.previous_school_name,
            "previous_school_country_id": application.previous_school_country_id,
            "previous_graduation_date": application.previous_graduation_date.isoformat()
            if application.previous_graduation_date
            else "",
            "personal_statement": application.personal_statement,
            "family_name": person.family_name,
            "given_name": person.given_name,
            "birth_date": person.birth_date.isoformat() if person.birth_date else "",
            "gender": person.gender,
            "nationality_country_id": person.nationality_id,
            "phone": person.phone,
            "address": person.address,
        }
        if data:
            values.update({key: value for key, value in data.items() if key in values})
        applicant_status = application.applicant_status()
        return render(
            request,
            self.template_name,
            {
                "title": str(cycle.name),
                "application": application,
                "status": applicant_status,
                "statuses": ApplicationStatus,
                "editable": application.status == ApplicationStatus.DRAFT,
                "identity_editable": can_edit_identity(person),
                "can_withdraw": applicant_status.is_open()
                and application.student_record_id is None
                and applicant_status != ApplicationStatus.ADMITTED,
                "offered_programs": sorted(
                    cycle.programs.select_related("program"), key=lambda offered: str(offered.program.name)
                ),
                "document_types": document_types,
                "countries": sorted(Country.objects.filter(is_active=True), key=lambda country: str(country.name)),
                "genders": Gender.choices,
                "values": values,
                "errors": errors or {},
            },
            status=status,
        )

    def post(self, request: HttpRequest, pk: int) -> HttpResponse:
        application = self._application(request, pk)
        action = request.POST.get("action", "")
        if action not in self.actions:
            return HttpResponseBadRequest()
        back = _redirect(request, reverse("portal:application", args=[application.pk]))
        try:
            if action in ("save", "submit"):
                return self._save(request, application, submit=action == "submit") or back
            if action == "respond":
                accept = request.POST.get("accept") == "1"
                RespondToOffer().handle(application, accept, request.user)
                messages.success(
                    request,
                    _("You accepted the offer. The registrar's office will create your student record.")
                    if accept
                    else _("You declined the offer."),
                )
            else:
                reason = (request.POST.get("reason") or "").strip()
                WithdrawApplication().handle(application, request.user, reason or None)
                messages.success(request, _("The application was withdrawn."))
        except PermissionDenied as error:
            raise Http404 from error
        except ValidationError as error:
            _flash_errors(request, error)
        return back

    def _save(self, request: HttpRequest, application: Application, *, submit: bool) -> HttpResponse | None:
        data = request.POST.dict()
        try:
            if can_edit_identity(application.person):
                UpdateApplicantPersonalDetails().handle(
                    request.user,
                    {key: data.get(key, "") for key in UpdateApplicantPersonalDetails.FIELDS if key in data},
                )
            UpdateApplication().handle(
                application, {key: data[key] for key in Application.APPLICANT_FIELDS if key in data}, request.user
            )
        except ValidationError as error:
            return self.render(request, application, _errors_by_field(error), data, status=_invalid_status(request))

        upload_errors: dict[str, list[str]] = {}
        attach = AttachApplicationDocument()
        for name, upload in request.FILES.items():
            if not name.startswith("document_"):
                continue
            type_id = _int(name.removeprefix("document_"))
            if type_id is None:
                continue
            try:
                attach.handle(application, type_id, upload, request.user)
            except ValidationError as error:
                upload_errors[f"uploads.{type_id}"] = list(error.messages)
        if upload_errors:
            application.refresh_from_db()
            return self.render(request, application, upload_errors, data, status=_invalid_status(request))

        if not submit:
            messages.success(request, _("Draft saved."))
            return None
        application.refresh_from_db()
        try:
            SubmitApplication().handle(application, request.user)
        except ValidationError as error:
            return self.render(request, application, _errors_by_field(error), data, status=_invalid_status(request))
        messages.success(request, _("Your application was submitted. We sent a confirmation to your email."))
        return None


def _int(value: Any) -> int | None:
    try:
        return int(value)
    except TypeError, ValueError:
        return None


#: Added to ``ninefruits.portal.urls`` (namespace ``portal``).
urlpatterns = [
    path("applications/", ApplicationsView.as_view(), name="applications"),
    path("applications/<int:pk>/", ApplicationDetailView.as_view(), name="application"),
]


def _show_applications(request: HttpRequest) -> bool:
    """Original portal layout: the applicant persona, or any cycle taking applications."""
    from ninefruits.portal.access import persona_values
    from ninefruits.security.enums import Persona

    if request.user.person_id is None:
        return False
    return (
        Persona.APPLICANT.value in persona_values(request) or AdmissionCycle.objects.accepting_applications().exists()
    )


def register_menu() -> None:
    from ninefruits.portal import menu

    menu.register(
        "applications",
        pgettext_lazy("portal", "Admissions"),
        "portal:applications",
        order=15,
        visible=_show_applications,
    )
