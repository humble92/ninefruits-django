"""Admission cycles and applications (original ``App\\Models\\Admission``, ADR 0008).

A cycle is an admission round, e.g. "2027 Spring regular admission", or a rolling cycle with no
deadline (``closes_at`` null). Cycles are separate from terms: the admission term is chosen when
an admitted applicant is matriculated. An application is one person applying to one program of
a cycle; uploaded documents are media in the ``documents`` collection with the custom property
``document_type_id``."""

from __future__ import annotations

from datetime import datetime
from typing import Any, ClassVar, Self

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.utils.translation import pgettext_lazy

from ninefruits.admission.enums import ApplicationStatus
from ninefruits.core.models import TimeStampedModel, VisibleQuerySet
from ninefruits.i18n.fields import TranslatableJSONField
from ninefruits.media.services import PDF_AND_IMAGES, HasMedia, MediaCollection
from ninefruits.security.enums import Permission

#: Code list of document types a cycle can ask for.
DOCUMENT_TYPE_LOOKUP = "application_document_type"
#: Code list of admission types (also on student records).
ADMISSION_TYPE_LOOKUP = "admission_type"
#: Files are checked against the admission settings (``max_document_size_mb``, at most 50);
#: this is only the media library's upper bound.
DOCUMENT_MAX_BYTES = 50 * 1024 * 1024


def _scope_for(user: Any, permission: Permission) -> Any:
    from ninefruits.security.services.authorization import authorization

    return authorization().scope_for(user, permission)


class AdmissionCycleQuerySet(VisibleQuerySet):
    def accepting_applications(self, at: datetime | None = None) -> Self:
        """Published cycles taking applications at the time."""
        at = at or timezone.now()
        return self.filter(is_published=True, opens_at__lte=at).filter(Q(closes_at__isnull=True) | Q(closes_at__gt=at))


class AdmissionCycle(TimeStampedModel):
    code = models.CharField(
        pgettext_lazy("reference", "Code"),
        max_length=64,
        unique=True,
        help_text=_("Short identifier used in application numbers, e.g. 2027-SPRING."),
    )
    name = TranslatableJSONField(pgettext_lazy("reference", "Name"))
    description = TranslatableJSONField(
        pgettext_lazy("admissions", "Description"), null=True, blank=True, max_length=2000
    )
    opens_at = models.DateTimeField(pgettext_lazy("admissions", "Opens"))
    closes_at = models.DateTimeField(
        pgettext_lazy("admissions", "Closes"),
        null=True,
        blank=True,
        help_text=_("Leave empty for rolling admission without a deadline."),
    )
    is_published = models.BooleanField(
        pgettext_lazy("admissions.fields", "Published"),
        default=False,
        help_text=_("Applicants can see and apply to published cycles between the opening and closing times."),
    )
    should_release_decisions_immediately = models.BooleanField(
        _("Release decisions immediately"),
        default=False,
        help_text=_(
            "Tell each applicant as soon as they are decided. Otherwise decisions are released together "
            "with the release action."
        ),
    )
    offer_response_days = models.SmallIntegerField(
        _("Days to accept an offer"),
        null=True,
        blank=True,
        help_text=_("Admitted applicants must accept within this many days after the release. Empty: no deadline."),
    )

    objects = AdmissionCycleQuerySet.as_manager()

    class Meta:
        db_table = "admission_cycles"
        ordering = ["-opens_at", "code"]
        verbose_name = _("admission cycle")
        verbose_name_plural = _("admission cycles")

    def __str__(self) -> str:
        return str(self.name or self.code)

    def __repr__(self) -> str:
        return f"<AdmissionCycle {self.pk} {self.code}>"

    def clean(self) -> None:
        super().clean()
        if self.closes_at is not None and self.opens_at is not None and self.closes_at <= self.opens_at:
            raise ValidationError({"closes_at": _("The closing time must be after the opening time.")})
        if self.offer_response_days is not None and not 1 <= self.offer_response_days <= 365:
            raise ValidationError({"offer_response_days": _("Enter a number between 1 and 365.")})

    def is_accepting_applications(self, at: datetime | None = None) -> bool:
        at = at or timezone.now()
        return self.is_published and self.opens_at <= at and (self.closes_at is None or self.closes_at > at)

    def is_rolling(self) -> bool:
        return self.closes_at is None


class AdmissionCycleProgram(TimeStampedModel):
    """A program offered in a cycle. Capacity is shown to staff when deciding; it is not
    enforced (decisions are a human judgement)."""

    admission_cycle = models.ForeignKey(
        AdmissionCycle, on_delete=models.CASCADE, related_name="programs", verbose_name=_("Admission cycle")
    )
    program = models.ForeignKey(
        "organization.Program",
        on_delete=models.RESTRICT,
        related_name="admission_cycle_programs",
        verbose_name=pgettext_lazy("security", "Program"),
    )
    capacity = models.IntegerField(pgettext_lazy("admissions", "Capacity"), null=True, blank=True)

    objects = VisibleQuerySet.as_manager()

    class Meta:
        db_table = "admission_cycle_programs"
        verbose_name = _("program offered")
        verbose_name_plural = _("Programs offered")
        constraints = [
            models.UniqueConstraint(
                fields=["admission_cycle", "program"],
                name="admission_cycle_programs_admission_cycle_id_program_id_unique",
            )
        ]

    def __str__(self) -> str:
        return str(self.program)

    def __repr__(self) -> str:
        return f"<AdmissionCycleProgram {self.pk} cycle={self.admission_cycle_id} program={self.program_id}>"


class AdmissionCycleDocumentType(TimeStampedModel):
    """A document applicants upload in a cycle (code list ``application_document_type``)."""

    admission_cycle = models.ForeignKey(
        AdmissionCycle, on_delete=models.CASCADE, related_name="document_types", verbose_name=_("Admission cycle")
    )
    document_type = models.ForeignKey(
        "institution.LookupValue",
        on_delete=models.RESTRICT,
        related_name="+",
        verbose_name=_("Document"),
    )
    is_required = models.BooleanField(pgettext_lazy("admissions", "Required"), default=True)

    objects = VisibleQuerySet.as_manager()

    class Meta:
        db_table = "admission_cycle_document_types"
        verbose_name = _("document")
        verbose_name_plural = _("Documents")
        constraints = [
            models.UniqueConstraint(
                fields=["admission_cycle", "document_type"],
                name="admission_cycle_document_types_admission_cycle_id_document_type_id_unique",
            )
        ]

    def __str__(self) -> str:
        return str(self.document_type)

    def __repr__(self) -> str:
        return f"<AdmissionCycleDocumentType {self.pk} cycle={self.admission_cycle_id}>"


class ApplicationQuerySet(VisibleQuerySet):
    def visible_to(self, user: Any) -> Self:
        """Staff by scope of ``applications.view`` or ``applications.review``, and the applicant's
        own applications. Mirrors the row level security policies on ``applications``."""
        scope = _scope_for(user, Permission.APPLICATIONS_VIEW).merge(_scope_for(user, Permission.APPLICATIONS_REVIEW))
        if scope.is_global:
            return self
        condition = Q(pk__in=[])
        if scope.org_unit_ids:
            condition |= Q(org_unit_id__in=scope.org_unit_ids)
        if scope.program_ids:
            condition |= Q(program_id__in=scope.program_ids)
        if getattr(user, "person_id", None) is not None:
            condition |= Q(person_id=user.person_id)
        return self.filter(condition)

    def open(self) -> Self:
        return self.filter(status__in=ApplicationStatus.open_values())


class Application(HasMedia, TimeStampedModel):
    DOCUMENTS_COLLECTION: ClassVar[str] = "documents"
    #: Fields the applicant fills in on the form.
    APPLICANT_FIELDS: ClassVar[tuple[str, ...]] = (
        "program_id",
        "admission_type_id",
        "previous_school_name",
        "previous_school_country_id",
        "previous_graduation_date",
        "personal_statement",
    )
    media_collections: ClassVar[dict[str, MediaCollection]] = {
        "documents": MediaCollection("documents", accepts=PDF_AND_IMAGES, max_size=DOCUMENT_MAX_BYTES),
    }

    application_number = models.CharField(_("Application number"), max_length=80, null=True, blank=True, unique=True)
    admission_cycle = models.ForeignKey(
        AdmissionCycle, on_delete=models.RESTRICT, related_name="applications", verbose_name=_("Admission cycle")
    )
    person = models.ForeignKey(
        "person.Person", on_delete=models.RESTRICT, related_name="applications", verbose_name=_("Person")
    )
    program = models.ForeignKey(
        "organization.Program",
        on_delete=models.RESTRICT,
        related_name="applications",
        verbose_name=pgettext_lazy("security", "Program"),
    )
    org_unit = models.ForeignKey(
        "organization.OrgUnit", on_delete=models.RESTRICT, related_name="applications", verbose_name=_("Org unit")
    )
    admission_type = models.ForeignKey(
        "institution.LookupValue",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
        verbose_name=_("Admission type"),
    )
    status = models.CharField(
        pgettext_lazy("admissions", "Status"),
        max_length=32,
        choices=ApplicationStatus.choices,
        default=ApplicationStatus.DRAFT,
    )
    previous_school_name = models.CharField(_("Previous school"), max_length=255, null=True, blank=True)
    previous_school_country = models.ForeignKey(
        "institution.Country",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
        verbose_name=_("Country of previous school"),
    )
    previous_graduation_date = models.DateField(_("Graduation date (previous school)"), null=True, blank=True)
    personal_statement = models.TextField(_("Personal statement"), null=True, blank=True)
    submitted_at = models.DateTimeField(pgettext_lazy("admissions.fields", "Submitted"), null=True, blank=True)
    review_started_at = models.DateTimeField(null=True, blank=True)
    decided_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
        verbose_name=pgettext_lazy("admissions", "Decided by"),
    )
    decided_at = models.DateTimeField(pgettext_lazy("admissions", "Decided"), null=True, blank=True)
    decision_note = models.TextField(pgettext_lazy("admissions", "Decision note"), null=True, blank=True)
    decision_released_at = models.DateTimeField(pgettext_lazy("admissions", "Released"), null=True, blank=True)
    offer_expires_at = models.DateTimeField(_("Offer deadline"), null=True, blank=True)
    responded_at = models.DateTimeField(null=True, blank=True)
    withdrawn_at = models.DateTimeField(null=True, blank=True)
    withdrawal_reason = models.TextField(null=True, blank=True)
    student_record = models.OneToOneField(
        "person.StudentRecord",
        on_delete=models.RESTRICT,
        null=True,
        blank=True,
        related_name="application",
        verbose_name=_("Student record"),
    )
    matriculated_at = models.DateTimeField(null=True, blank=True)

    objects = ApplicationQuerySet.as_manager()

    class Meta:
        db_table = "applications"
        ordering = ["-created_at", "-id"]
        verbose_name = _("application")
        verbose_name_plural = _("applications")

    def __str__(self) -> str:
        return self.application_number or f"#{self.pk}"

    def __repr__(self) -> str:
        return f"<Application {self.pk} {self.status}>"

    @property
    def application_status(self) -> ApplicationStatus:
        return ApplicationStatus(self.status)

    def is_owned_by(self, user: Any) -> bool:
        person_id = getattr(user, "person_id", None)
        return person_id is not None and person_id == self.person_id

    def is_in_scope_of(self, user: Any, permission: Permission) -> bool:
        """Whether the user holds the permission in a scope that covers this application."""
        return bool(_scope_for(user, permission).covers(self.org_unit_id, self.program_id))

    def is_visible_to(self, user: Any) -> bool:
        return (
            self.is_owned_by(user)
            or self.is_in_scope_of(user, Permission.APPLICATIONS_VIEW)
            or self.is_in_scope_of(user, Permission.APPLICATIONS_REVIEW)
        )

    def is_decision_visible_to_applicant(self) -> bool:
        """The decision as the applicant may see it: hidden until released."""
        return self.decision_released_at is not None

    def applicant_status(self) -> ApplicationStatus:
        """Status as shown to the applicant: a decided but unreleased application still looks
        under review."""
        status = self.application_status
        if status.is_decided() and not self.is_decision_visible_to_applicant():
            return ApplicationStatus.UNDER_REVIEW
        return status

    def is_decision_changeable(self) -> bool:
        status = self.application_status
        return status.is_awaiting_decision() or (status.is_decided() and not self.is_decision_visible_to_applicant())

    def documents_of_type(self, document_type_id: int) -> list[Any]:
        """Uploaded documents of one type (media custom property ``document_type_id``)."""
        return [
            media
            for media in self.get_media(self.DOCUMENTS_COLLECTION)
            if _int(media.custom_property("document_type_id")) == int(document_type_id)
        ]


def _int(value: Any) -> int | None:
    try:
        return int(value)
    except TypeError, ValueError:
        return None


class ApplicationNumberSequence(models.Model):
    """Per-cycle counter of application numbers (``SubmitApplication``). Not audited."""

    admission_cycle = models.OneToOneField(
        AdmissionCycle, on_delete=models.CASCADE, primary_key=True, related_name="number_sequence"
    )
    last_value = models.IntegerField(default=0)

    objects = VisibleQuerySet.as_manager()

    class Meta:
        db_table = "application_number_sequences"

    def __str__(self) -> str:
        return f"{self.admission_cycle_id}: {self.last_value}"
