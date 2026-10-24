"""Portal pages of people and student records (original Livewire ``MyRecords``, ``MyProfile``
and ``Advisees``), mounted in the ``portal`` namespace.

One Livewire component -> one view: GET renders the page, POST runs ``action`` and redirects
back with a message (HTMX posts get an ``HX-Redirect``). Under row level security students only
reach their own records; requests are possible only on current records and graduates see their
records read only."""

from __future__ import annotations

from typing import Any

from django import forms
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied, ValidationError
from django.http import Http404, HttpRequest, HttpResponse, HttpResponseBadRequest, HttpResponseRedirect
from django.shortcuts import get_object_or_404, render
from django.urls import path, reverse
from django.utils import timezone
from django.utils.translation import gettext as _
from django.utils.translation import pgettext_lazy
from django.views import View

from ninefruits.organization.models import Program
from ninefruits.person.actions import (
    CancelAdditionalProgramRequest,
    CancelStatusChange,
    RequestAdditionalProgram,
    RequestStatusChange,
    UpdateOwnContactDetails,
)
from ninefruits.person.enums import (
    AdditionalProgramRole,
    GuardianRelationship,
    StatusChangeStatus,
    StudentStatus,
)
from ninefruits.person.models import (
    AdditionalProgramRequest,
    AdvisorAssignment,
    Guardian,
    Person,
    StudentRecord,
    StudentStatusChange,
    StudentStatusChangeType,
)
from ninefruits.person.services import CurrentStudentRecord
from ninefruits.term.enums import TermWindowType
from ninefruits.term.services.term_resolver import TermResolver


def _back(request: HttpRequest, url_name: str) -> HttpResponse:
    url = reverse(url_name)
    if request.headers.get("HX-Request"):
        response = HttpResponse(status=204)
        response["HX-Redirect"] = url
        return response
    return HttpResponseRedirect(url)


def _flash_errors(request: HttpRequest, error: ValidationError) -> None:
    for message in error.messages:
        messages.error(request, message)


class _PersonRequiredMixin(LoginRequiredMixin):
    def dispatch(self, request: HttpRequest, *args: Any, **kwargs: Any) -> Any:
        if request.user.is_authenticated and request.user.person_id is None:
            raise Http404
        return super().dispatch(request, *args, **kwargs)


class StatusChangeRequestForm(forms.Form):
    status_change_type = forms.ModelChoiceField(queryset=StudentStatusChangeType.objects.none())
    effective_date = forms.DateField()
    reason = forms.CharField(max_length=2000)

    def __init__(self, *args: Any, types: list[StudentStatusChangeType], **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.fields["status_change_type"].queryset = StudentStatusChangeType.objects.filter(  # type: ignore[attr-defined]
            pk__in=[change_type.pk for change_type in types]
        )


class AdditionalProgramForm(forms.Form):
    program = forms.ModelChoiceField(queryset=Program.objects.none())
    role = forms.ChoiceField(choices=AdditionalProgramRole.choices)
    statement = forms.CharField(max_length=2000, required=False)

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.fields["program"].queryset = Program.objects.effective_on()  # type: ignore[attr-defined]


class MyRecordsView(_PersonRequiredMixin, View):
    template_name = "person/portal/records.html"

    def get(self, request: HttpRequest) -> HttpResponse:
        current = CurrentStudentRecord(request.session)
        record = current.get(request.user)
        context: dict[str, Any] = {
            "title": _("My records"),
            "records": current.all(request.user),
            "record": record,
            "today": timezone.localdate().isoformat(),
            "roles": AdditionalProgramRole.choices,
        }
        if record is not None:
            active = StudentStatus(record.status).is_active()
            changes = list(record.status_changes.select_related("type").order_by("-requested_at", "-id"))
            application_term = None
            if active:
                terms = TermResolver().terms_open_for(TermWindowType.ADDITIONAL_PROGRAM_APPLICATION, record)
                application_term = terms[0] if terms else None
            role = request.GET.get("role", AdditionalProgramRole.SECOND_MAJOR)
            if role not in AdditionalProgramRole.values:
                role = AdditionalProgramRole.SECOND_MAJOR
            options = []
            if application_term is not None:
                flag = "allows_minor" if role == AdditionalProgramRole.MINOR else "allows_second_major"
                options = sorted(
                    Program.objects.effective_on().filter(**{flag: True}).exclude(pk=record.program_id),
                    key=lambda program: str(program.name),
                )
            context.update(
                {
                    "status_label": StudentStatus(record.status).label,
                    "advisors": [
                        assignment.instructor.person.display_name()
                        for assignment in record.advisor_assignments.filter(end_date__isnull=True).select_related(
                            "instructor__person"
                        )
                    ],
                    "requestable_types": self._requestable_types(record) if active else [],
                    "pending": next(
                        (change for change in changes if change.status == StatusChangeStatus.REQUESTED), None
                    ),
                    "changes": changes,
                    "additional_programs": list(
                        record.additional_programs.select_related("program").order_by("start_date")
                    ),
                    "additional_requests": list(
                        AdditionalProgramRequest.objects.filter(student_record=record)
                        .select_related("program", "term")
                        .order_by("-requested_at")
                    ),
                    "application_term": application_term,
                    "additional_options": options,
                    "selected_role": role,
                }
            )
        return render(request, self.template_name, context)

    @staticmethod
    def _requestable_types(record: StudentRecord) -> list[StudentStatusChangeType]:
        return [
            change_type
            for change_type in StudentStatusChangeType.objects.filter(can_student_request=True, is_active=True)
            if change_type.applies_from(record.status)
        ]

    def post(self, request: HttpRequest) -> HttpResponse:
        action = request.POST.get("action", "")
        handler = getattr(self, f"do_{action}", None)
        if (
            action
            not in {"choose", "request_change", "cancel", "apply_additional_program", "cancel_additional_program"}
            or handler is None
        ):
            return HttpResponseBadRequest()
        try:
            handler(request)
        except ValidationError as error:
            _flash_errors(request, error)
        return _back(request, "portal:records")

    def _current(self, request: HttpRequest) -> StudentRecord:
        record = CurrentStudentRecord(request.session).get(request.user)
        if record is None:
            raise Http404
        return record

    def do_choose(self, request: HttpRequest) -> None:
        CurrentStudentRecord(request.session).choose(request.user, int(request.POST.get("record_id") or 0))

    def do_request_change(self, request: HttpRequest) -> None:
        record = self._current(request)
        form = StatusChangeRequestForm(request.POST, types=self._requestable_types(record))
        if not form.is_valid():
            raise ValidationError(form.errors.as_data())
        data = form.cleaned_data
        RequestStatusChange().handle(
            record, data["status_change_type"], data["effective_date"], data["reason"], request.user
        )
        messages.success(request, _("Your request was submitted. The registrar's office will review it."))

    def do_cancel(self, request: HttpRequest) -> None:
        change = get_object_or_404(
            StudentStatusChange, pk=request.POST.get("change_id") or 0, requested_by=request.user
        )
        CancelStatusChange().handle(change, request.user)

    def do_apply_additional_program(self, request: HttpRequest) -> None:
        record = self._current(request)
        form = AdditionalProgramForm(request.POST)
        if not form.is_valid():
            raise ValidationError(form.errors.as_data())
        data = form.cleaned_data
        RequestAdditionalProgram().handle(
            record, data["program"], data["role"], data["statement"] or None, request.user
        )
        messages.success(request, _("Your application was submitted. The program's office will review it."))

    def do_cancel_additional_program(self, request: HttpRequest) -> None:
        application = get_object_or_404(AdditionalProgramRequest, pk=request.POST.get("request_id") or 0)
        try:
            CancelAdditionalProgramRequest().handle(application, request.user)
        except PermissionDenied as error:
            raise Http404 from error


class GuardianForm(forms.Form):
    relationship = forms.ChoiceField(choices=GuardianRelationship.choices)
    full_name = forms.CharField(max_length=255)
    phone = forms.CharField(max_length=32, required=False)
    email = forms.EmailField(max_length=255, required=False)
    is_primary_contact = forms.BooleanField(required=False)


class MyProfileView(_PersonRequiredMixin, View):
    """A person's own contact details and guardians. Names, birth date and identity numbers are
    changed by the registrar."""

    template_name = "person/portal/profile.html"

    def get(self, request: HttpRequest) -> HttpResponse:
        person = get_object_or_404(Person, pk=request.user.person_id)
        return render(
            request,
            self.template_name,
            {
                "title": _("My details"),
                "person": person,
                "guardians": list(person.guardians.all()),
                "relationships": GuardianRelationship.choices,
                "contact_fields": [
                    ("email", _("Contact email"), person.email),
                    ("phone", _("Phone"), person.phone),
                    ("postal_code", _("Postal code"), person.postal_code),
                ],
            },
        )

    def post(self, request: HttpRequest) -> HttpResponse:
        action = request.POST.get("action", "")
        if action not in {"save_contact", "add_guardian", "remove_guardian"}:
            return HttpResponseBadRequest()
        try:
            getattr(self, f"do_{action}")(request)
        except ValidationError as error:
            _flash_errors(request, error)
        return _back(request, "portal:profile")

    def do_save_contact(self, request: HttpRequest) -> None:
        UpdateOwnContactDetails().handle(request.user, request.POST.dict())
        messages.success(request, _("Your details were saved."))

    def do_add_guardian(self, request: HttpRequest) -> None:
        form = GuardianForm(request.POST)
        if not form.is_valid():
            raise ValidationError(form.errors.as_data())
        data = form.cleaned_data
        Guardian.objects.create(
            person_id=request.user.person_id,
            relationship=data["relationship"],
            full_name=data["full_name"],
            phone=data["phone"] or None,
            email=data["email"] or None,
            is_primary_contact=data["is_primary_contact"],
        )

    def do_remove_guardian(self, request: HttpRequest) -> None:
        get_object_or_404(Guardian, pk=request.POST.get("guardian_id") or 0, person_id=request.user.person_id).delete()


class AdviseesView(_PersonRequiredMixin, View):
    """Advisors see the students they currently advise."""

    template_name = "person/portal/advisees.html"

    def get(self, request: HttpRequest) -> HttpResponse:
        assignments = sorted(
            AdvisorAssignment.objects.current()
            .filter(instructor__person_id=request.user.person_id)
            .select_related("student_record__person", "student_record__program"),
            key=lambda assignment: assignment.student_record.student_number,
        )
        rows = [
            {
                "student_number": assignment.student_record.student_number,
                "name": assignment.student_record.person.display_name(),
                "program": assignment.student_record.program,
                "year_level": assignment.student_record.year_level,
                "status": StudentStatus(assignment.student_record.status).label,
            }
            for assignment in assignments
        ]
        return render(request, self.template_name, {"title": _("Advisees"), "rows": rows})


#: Added to ``ninefruits.portal.urls`` (namespace ``portal``).
urlpatterns = [
    path("records/", MyRecordsView.as_view(), name="records"),
    path("profile/", MyProfileView.as_view(), name="profile"),
    path("advisees/", AdviseesView.as_view(), name="advisees"),
]


def register_menu() -> None:
    from ninefruits.portal import menu
    from ninefruits.security.enums import Persona

    menu.register(
        "records",
        pgettext_lazy("portal", "My records"),
        "portal:records",
        order=20,
        personas={Persona.STUDENT, Persona.ALUMNI},
    )
    menu.register(
        "profile",
        pgettext_lazy("portal", "My details"),
        "portal:profile",
        order=60,
        visible=lambda request: request.user.person_id is not None,
    )
    menu.register(
        "advisees", pgettext_lazy("portal", "Advisees"), "portal:advisees", order=80, personas={Persona.ADVISOR}
    )
