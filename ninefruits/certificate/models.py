"""Certificates (original ``App\\Models\\Certificate\\*``, ADR 0013).

- :class:`CertificateType`: a kind of certificate (enrollment, graduation, transcript, ...) with
  a template per language the institution edits. Configuration data (no row level security).
- :class:`CertificateTemplate`: the wording of a kind in one language.
- :class:`CertificateNumberSequence`: the per-prefix counter of the serial numbers.
- :class:`CertificateIssue`: the issue ledger. Never edited or deleted; revoked with a reason
  (status only), the stored PDF stays."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, ClassVar, Self

from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.utils.translation import pgettext_lazy

from ninefruits.certificate.enums import CertificateAudience, CertificateIssueStatus
from ninefruits.core.models import TimeStampedModel, VisibleQuerySet
from ninefruits.i18n.fields import TranslatableJSONField
from ninefruits.i18n.translation import translate
from ninefruits.media.services import PDF, HasMedia, MediaCollection

if TYPE_CHECKING:
    from ninefruits.media.models import Media


class CertificateType(TimeStampedModel):
    """A kind of certificate (legacy FCERT with one PDFlib script per kind and language)."""

    code = models.CharField(
        pgettext_lazy("reference", "Code"),
        max_length=32,
        unique=True,
        help_text=_("Used in serial numbers, e.g. ENR, GRD, TRN."),
    )
    name = TranslatableJSONField(pgettext_lazy("reference", "Name"))
    name_translations: dict[str, str]  # TranslationsAccessor, set by the field
    audience = models.CharField(
        pgettext_lazy("certificate", "For"),
        max_length=16,
        choices=CertificateAudience.choices,
        default=CertificateAudience.ANY,
    )
    has_grades = models.BooleanField(
        _("Includes grades"),
        default=False,
        help_text=_("Adds a table of the finalized grades by term (transcript)."),
    )
    has_photo = models.BooleanField(_("Includes photo"), default=False)
    is_active = models.BooleanField(pgettext_lazy("reference.fields", "Active"), default=True)
    sort_order = models.IntegerField(_("Order"), default=0)

    objects = VisibleQuerySet.as_manager()

    class Meta:
        db_table = "certificate_types"
        ordering = ["sort_order", "id"]
        verbose_name = _("Certificate kind")
        verbose_name_plural = _("Certificate kinds")

    def __str__(self) -> str:
        return str(self.name or self.code)

    def __repr__(self) -> str:
        return f"<CertificateType {self.pk} {self.code}>"

    def name_in(self, locale: str) -> str:
        """The name in the given language (falling back like ``util.i18n``)."""
        return translate(self.name_translations, locale) or self.code


class CertificateTemplate(TimeStampedModel):
    """The wording of a kind in one language: title, body paragraphs with ``{placeholders}``,
    footer and signer."""

    certificate_type = models.ForeignKey(
        CertificateType,
        on_delete=models.CASCADE,
        related_name="templates",
        verbose_name=pgettext_lazy("certificate", "Kind"),
    )
    locale = models.CharField(pgettext_lazy("common", "Language"), max_length=8)
    title = models.CharField(pgettext_lazy("certificate", "Title"), max_length=160)
    body = models.TextField(_("Body"))
    footer = models.TextField(_("Footer"), null=True, blank=True)
    signer = models.CharField(
        _("Signer"),
        max_length=160,
        null=True,
        blank=True,
        help_text=_("Overrides the signer from the certificate settings for this language."),
    )

    objects = VisibleQuerySet.as_manager()

    class Meta:
        db_table = "certificate_templates"
        ordering = ["locale", "id"]
        verbose_name = _("Templates")
        verbose_name_plural = _("Templates")
        constraints = [
            models.UniqueConstraint(
                fields=["certificate_type", "locale"], name="certificate_templates_certificate_type_id_locale_unique"
            )
        ]

    def __str__(self) -> str:
        return f"{self.title} ({self.locale})"

    def __repr__(self) -> str:
        return f"<CertificateTemplate {self.pk} type={self.certificate_type_id} {self.locale}>"


class CertificateNumberSequence(models.Model):
    """Per-prefix counter of the serial numbers (``CertificateSerialGenerator``)."""

    prefix = models.CharField(max_length=64, primary_key=True)
    last_value = models.BigIntegerField(default=0)
    created_at = models.DateTimeField(null=True, blank=True, default=timezone.now, editable=False)
    updated_at = models.DateTimeField(null=True, blank=True, auto_now=True, editable=False)

    objects = VisibleQuerySet.as_manager()

    class Meta:
        db_table = "certificate_number_sequences"

    def __str__(self) -> str:
        return self.prefix


class CertificateIssueQuerySet(VisibleQuerySet):
    def visible_to(self, user: Any) -> Self:
        """Issues of student records the user can see (the student's own included). Mirrors the
        row level security policy ``certificate_issues_record_select``."""
        from ninefruits.person.models import StudentRecord

        return self.filter(student_record_id__in=StudentRecord.objects.visible_to(user).values("pk"))

    def issued(self) -> Self:
        return self.filter(status=CertificateIssueStatus.ISSUED)


class CertificateIssue(HasMedia, TimeStampedModel):
    """An issued certificate: the ledger row, the stored PDF and the verification code."""

    PDF_COLLECTION: ClassVar[str] = "pdf"
    media_collections: ClassVar[dict[str, MediaCollection]] = {
        "pdf": MediaCollection("pdf", single_file=True, accepts=PDF),
    }

    student_record = models.ForeignKey(
        "person.StudentRecord",
        on_delete=models.RESTRICT,
        related_name="certificate_issues",
        verbose_name=_("student record"),
    )
    certificate_type = models.ForeignKey(
        CertificateType,
        on_delete=models.RESTRICT,
        related_name="issues",
        verbose_name=pgettext_lazy("certificate", "Kind"),
    )
    locale = models.CharField(pgettext_lazy("common", "Language"), max_length=8)
    serial_number = models.CharField(_("Serial number"), max_length=64, unique=True)
    verification_code = models.CharField(_("Verification code"), max_length=40, unique=True)
    purpose = models.CharField(_("Purpose"), max_length=200, null=True, blank=True)
    copies = models.SmallIntegerField(_("Copies"), default=1, validators=[MinValueValidator(1), MaxValueValidator(20)])
    status = models.CharField(
        pgettext_lazy("registration", "Status"),
        max_length=16,
        choices=CertificateIssueStatus.choices,
        default=CertificateIssueStatus.ISSUED,
    )
    issued_at = models.DateTimeField(pgettext_lazy("certificate.fields", "Issued"))
    issued_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
        verbose_name=_("Issued by"),
    )
    pdf_checksum = models.CharField(max_length=64, null=True, blank=True)
    revoked_at = models.DateTimeField(null=True, blank=True)
    revoked_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )
    revocation_reason = models.TextField(null=True, blank=True)

    objects = CertificateIssueQuerySet.as_manager()

    class Meta:
        db_table = "certificate_issues"
        ordering = ["-issued_at", "-id"]
        verbose_name = _("Issued certificate")
        verbose_name_plural = _("Issued certificates")

    def __str__(self) -> str:
        return self.serial_number

    def __repr__(self) -> str:
        # The serial number identifies a document, not a person; the holder stays out.
        return f"<CertificateIssue {self.pk} {self.serial_number} {self.status}>"

    @property
    def is_revoked(self) -> bool:
        return self.status == CertificateIssueStatus.REVOKED

    def pdf(self) -> Media | None:
        """The stored PDF (a ``Media`` row) or ``None``."""
        return self.get_first_media(self.PDF_COLLECTION)
