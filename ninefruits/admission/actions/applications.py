"""The applicant's side of an application (original ``StartApplication``, ``UpdateApplication``,
``UpdateApplicantPersonalDetails``, ``AttachApplicationDocument``, ``SubmitApplication`` and
``WithdrawApplication``)."""

from __future__ import annotations

from typing import IO, Any

from django import forms
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import IntegrityError, connection, transaction
from django.utils import timezone
from django.utils.translation import gettext as _

from ninefruits.admission.enums import ApplicationStatus
from ninefruits.admission.models import (
    ADMISSION_TYPE_LOOKUP,
    AdmissionCycle,
    AdmissionCycleDocumentType,
    Application,
)
from ninefruits.admission.settings import AdmissionSettings
from ninefruits.audit.logger import audit
from ninefruits.institution.models import Country, LookupValue
from ninefruits.media.models import Media
from ninefruits.media.services import FileUnacceptableForCollection, add_media, delete_media
from ninefruits.organization.models import Program
from ninefruits.person.enums import Gender
from ninefruits.person.models import Instructor, Person, StudentRecord

_NEXT_NUMBER_SQL = (
    "INSERT INTO application_number_sequences (admission_cycle_id, last_value) VALUES (%s, 1) "
    "ON CONFLICT (admission_cycle_id) DO UPDATE SET last_value = application_number_sequences.last_value + 1 "
    "RETURNING last_value"
)


class StartApplication:
    """Creates a draft application of the signed-in person. One open application per cycle;
    graduates and current students apply with the same account."""

    def handle(self, applicant: Any, cycle: AdmissionCycle, program: Program) -> Application:
        if applicant.person_id is None:
            raise ValidationError({"admission_cycle_id": _("This account is not linked to a person.")})
        if not cycle.is_accepting_applications():
            raise ValidationError({"admission_cycle_id": _("This cycle is not taking applications.")})
        ensure_offered(cycle, program)

        try:
            # Own savepoint: on PostgreSQL a failed statement would abort the caller's transaction.
            with transaction.atomic():
                application = Application.objects.create(
                    admission_cycle=cycle,
                    person_id=applicant.person_id,
                    program=program,
                    org_unit_id=program.org_unit_id,
                )
        except IntegrityError as error:
            if getattr(error.__cause__, "sqlstate", None) != "23505":
                raise
            raise ValidationError(
                {"admission_cycle_id": _("You already have an open application in this cycle.")}
            ) from error

        audit(
            "application.started",
            application,
            properties={"cycle": cycle.code, "program": program.code},
            causer=applicant,
        )
        return application

    __call__ = handle


def ensure_offered(cycle: AdmissionCycle, program: Program) -> None:
    if not cycle.programs.filter(program_id=program.pk).exists():
        raise ValidationError({"program_id": _("This program is not offered in the cycle.")})


def ensure_editable_by(application: Application, applicant: Any) -> None:
    if not application.is_owned_by(applicant):
        raise PermissionDenied
    if application.status != ApplicationStatus.DRAFT:
        raise ValidationError({"status": _("Only applications that have not been submitted can be changed.")})


class _ApplicationForm(forms.Form):
    program_id = forms.IntegerField(required=False)
    admission_type_id = forms.IntegerField(required=False)
    previous_school_name = forms.CharField(max_length=255, required=False)
    previous_school_country_id = forms.IntegerField(required=False)
    previous_graduation_date = forms.DateField(required=False)
    personal_statement = forms.CharField(max_length=10000, required=False, strip=False)


class UpdateApplication:
    """The applicant edits a draft. Changes are recorded by the data audit trigger; drafts are
    not business decisions, so no audit entry with a reason."""

    def handle(self, application: Application, data: dict[str, Any], applicant: Any) -> Application:
        ensure_editable_by(application, applicant)
        submitted = {key: value for key, value in data.items() if key in Application.APPLICANT_FIELDS}
        form = _ApplicationForm(data={key: "" if value is None else value for key, value in submitted.items()})
        if not form.is_valid():
            raise ValidationError(form.errors.as_data())
        cleaned = {key: form.cleaned_data[key] for key in submitted}

        program_id = cleaned.get("program_id")
        if program_id and int(program_id) != application.program_id:
            program = Program.objects.filter(pk=program_id).first()
            if program is None:
                raise ValidationError({"program_id": _("This program is not offered in the cycle.")})
            ensure_offered(application.admission_cycle, program)
            application.org_unit_id = program.org_unit_id
            application.program = program
        country_id = cleaned.get("previous_school_country_id")
        if country_id and not Country.objects.filter(pk=country_id).exists():
            raise ValidationError({"previous_school_country_id": _("Select a valid choice.")})
        admission_type_id = cleaned.get("admission_type_id")
        if (
            admission_type_id
            and not LookupValue.objects.of_type(ADMISSION_TYPE_LOOKUP).filter(pk=admission_type_id).exists()
        ):
            raise ValidationError({"admission_type_id": _("Select a valid choice.")})

        for key, value in cleaned.items():
            if key == "program_id":
                continue
            setattr(application, key, value if value not in ("", None) else None)
        application.save()
        return application

    __call__ = handle


class _PersonalDetailsForm(forms.Form):
    family_name = forms.CharField(max_length=255)
    given_name = forms.CharField(max_length=255, required=False)
    birth_date = forms.DateField(required=False)
    gender = forms.ChoiceField(choices=[("", "-"), *Gender.choices], required=False)
    nationality_country_id = forms.IntegerField(required=False)
    email = forms.EmailField(max_length=255, required=False)
    phone = forms.CharField(max_length=32, required=False)
    address = forms.CharField(max_length=1000, required=False)
    postal_code = forms.CharField(max_length=16, required=False)

    def clean_birth_date(self) -> Any:
        value = self.cleaned_data.get("birth_date")
        if value is not None and value >= timezone.localdate():
            raise ValidationError(_("The birth date must be a date before today."))
        return value

    def clean_nationality_country_id(self) -> Any:
        value = self.cleaned_data.get("nationality_country_id")
        if value and not Country.objects.filter(pk=value).exists():
            raise ValidationError(_("Select a valid choice."))
        return value


class UpdateApplicantPersonalDetails:
    """Applicants who have never been a student or instructor fill in their own name, birth date
    and other details on the application. Once a person has a student or instructor record these
    are kept by the registrar and only contact details remain self editable."""

    FIELDS = (
        "family_name",
        "given_name",
        "birth_date",
        "gender",
        "nationality_country_id",
        "email",
        "phone",
        "address",
        "postal_code",
    )

    def handle(self, applicant: Any, data: dict[str, Any]) -> Person:
        person = Person.objects.get(pk=applicant.person_id)
        if not can_edit_identity(person):
            raise ValidationError({"family_name": _("Your name and birth date are kept by the registrar's office.")})
        submitted = {key: value for key, value in data.items() if key in self.FIELDS}
        form = _PersonalDetailsForm(data={key: "" if value is None else value for key, value in submitted.items()})
        if not form.is_valid():
            raise ValidationError(form.errors.as_data())
        for key in submitted:
            value = form.cleaned_data[key]
            if key == "nationality_country_id":
                person.nationality_id = value or None
            else:
                setattr(person, key, value if value not in ("", None) else None)
        person.save()
        return person

    __call__ = handle


def can_edit_identity(person: Person) -> bool:
    return (
        not StudentRecord.objects.filter(person_id=person.pk).exists()
        and not Instructor.objects.filter(person_id=person.pk).exists()
    )


class AttachApplicationDocument:
    """Uploads a document of a type the cycle asks for. A new upload of the same type replaces
    the earlier one while the application is a draft."""

    def __init__(self, settings: AdmissionSettings | None = None) -> None:
        self._settings = settings

    def handle(self, application: Application, document_type_id: int, file: Any, applicant: Any) -> Media:
        ensure_editable_by(application, applicant)
        settings = self._settings or AdmissionSettings.load()
        if not application.admission_cycle.document_types.filter(document_type_id=document_type_id).exists():
            raise ValidationError({"document_type_id": _("This cycle does not ask for this document.")})
        if _size(file) > settings.max_document_size_mb * 1024 * 1024:
            raise ValidationError(
                {"document": _("The file is larger than %(mb)s MB.") % {"mb": settings.max_document_size_mb}}
            )

        with transaction.atomic():
            for existing in application.documents_of_type(document_type_id):
                delete_media(existing)
            try:
                return add_media(
                    application,
                    file,
                    Application.DOCUMENTS_COLLECTION,
                    custom_properties={"document_type_id": int(document_type_id)},
                )
            except FileUnacceptableForCollection as error:
                raise ValidationError({"document": _("Upload a PDF, JPEG or PNG file.")}) from error

    __call__ = handle


def _size(file: Any) -> int:
    size = getattr(file, "size", None)
    if isinstance(size, int):
        return size
    stream: IO[bytes] = getattr(file, "file", None) or file
    position = stream.tell()
    stream.seek(0, 2)
    end = stream.tell()
    stream.seek(position)
    return end


class SubmitApplication:
    """Submits a complete draft while the cycle is open and gives it its application number
    (``{cycle code}-{00001}``). After submission the applicant can no longer edit it."""

    def handle(self, application: Application, applicant: Any) -> Application:
        ensure_editable_by(application, applicant)
        cycle = application.admission_cycle
        if not cycle.is_accepting_applications():
            raise ValidationError({"status": _("This cycle is not taking applications.")})
        self.ensure_complete(application)

        with transaction.atomic():
            with connection.cursor() as cursor:
                cursor.execute(_NEXT_NUMBER_SQL, [cycle.pk])
                number = int(cursor.fetchone()[0])
            application.status = ApplicationStatus.SUBMITTED
            application.application_number = f"{cycle.code}-{number:05d}"
            application.submitted_at = timezone.now()
            application.save(update_fields=["status", "application_number", "submitted_at", "updated_at"])

        audit(
            "application.submitted",
            application,
            properties={"application_number": application.application_number},
            causer=applicant,
        )
        from ninefruits.admission.notifications import send_application_submitted

        transaction.on_commit(lambda: send_application_submitted(application, applicant))
        return application

    __call__ = handle

    @staticmethod
    def ensure_complete(application: Application) -> None:
        errors: dict[str, str] = {}
        if not (application.previous_school_name or "").strip():
            errors["previous_school_name"] = _("This field is required to submit.")
        if not (application.personal_statement or "").strip():
            errors["personal_statement"] = _("This field is required to submit.")
        missing = [
            str(required.document_type.name)
            for required in AdmissionCycleDocumentType.objects.filter(
                admission_cycle_id=application.admission_cycle_id, is_required=True
            )
            .select_related("document_type")
            .order_by("id")
            if not application.documents_of_type(required.document_type_id)
        ]
        if missing:
            errors["documents"] = _("Upload the required documents: %(documents)s.") % {"documents": ", ".join(missing)}
        if errors:
            raise ValidationError(errors)


class WithdrawApplication:
    """The applicant gives up an open application at any point before matriculation."""

    def handle(self, application: Application, applicant: Any, reason: str | None = None) -> Application:
        if not application.is_owned_by(applicant):
            raise PermissionDenied
        if not application.applicant_status().is_open() or application.student_record_id is not None:
            raise ValidationError({"status": _("This is not possible in the application's current status.")})
        application.status = ApplicationStatus.WITHDRAWN
        application.withdrawn_at = timezone.now()
        application.withdrawal_reason = reason or None
        application.save(update_fields=["status", "withdrawn_at", "withdrawal_reason", "updated_at"])
        audit("application.withdrawn", application, reason=reason or None, causer=applicant)
        return application

    __call__ = handle
