"""Builds a certificate (original ``CertificateRenderer``): the type's template in the issue's
language with its ``{placeholders}`` filled in, the facts table, the finalized grades for kinds
that include them, the photo, the serial number and a QR code to the public verification page.
Gotenberg (Chromium) renders the one layout, ``certificate/pdf/certificate.html``, to PDF.

Institutions change the wording (templates); the layout is code (ADR 0013). The placeholders a
template may use are listed in one place, :attr:`CertificateRenderer.PLACEHOLDERS`.

The whole document is rendered in the issue's language (labels, dates, the status). The content
is read in the system context: the caller (``IssueCertificate``) has checked that the staff
member may issue for the record, and a certificate must never come out incomplete because the
issuer's own row level security hides, say, grades."""

from __future__ import annotations

import base64
import re
from decimal import Decimal
from typing import Any, ClassVar

import qrcode
import qrcode.image.svg
from django.conf import settings
from django.core.exceptions import ValidationError
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils import translation
from django.utils.translation import gettext, pgettext

from ninefruits.certificate.data import CertificateContent
from ninefruits.certificate.enums import CertificateAudience
from ninefruits.certificate.models import CertificateIssue, CertificateTemplate
from ninefruits.certificate.services.serials import institution_now
from ninefruits.certificate.settings import CertificateSettings
from ninefruits.core.db import session_context
from ninefruits.i18n.formatting import format_ll

TEMPLATE = "certificate/pdf/certificate.html"
_PLACEHOLDER = re.compile(r"\{([a-z_]+)\}")
_PARAGRAPH_BREAK = re.compile(r"(?:\r\n|\r|\n){2,}")


def verification_url(code: str) -> str:
    """Absolute URL of the public verification page for a code (printed and in the QR code)."""
    return f"{str(settings.APP_URL).rstrip('/')}{reverse('certificate:verify', args=[code])}"


def qr_svg(url: str) -> str:
    """An inline SVG QR code (original bacon/bacon-qr-code ``SvgImageBackEnd``, no margin)."""
    code = qrcode.QRCode(border=0, image_factory=qrcode.image.svg.SvgPathImage)
    code.add_data(url)
    code.make(fit=True)
    return str(code.make_image().to_string(encoding="unicode"))


def institution_name(locale: str) -> str:
    from ninefruits.settings.groups.base import MissingSettings
    from ninefruits.settings.groups.institution import InstitutionSettings

    try:
        names = InstitutionSettings.load().name
    except MissingSettings:
        return str(settings.APP_NAME)
    if isinstance(names, dict) and names:
        return str(names.get(locale) or next(iter(names.values())) or settings.APP_NAME)
    return str(settings.APP_NAME)


def _number(value: Any) -> str:
    """``Decimal("18.0")`` -> ``"18"``, ``Decimal("18.5")`` -> ``"18.5"`` (PHP ``(string)(float)``)."""
    if value is None:
        return "0"
    text = format(Decimal(value).normalize(), "f")
    return text


class CertificateRenderer:
    #: Placeholders a template may use.
    PLACEHOLDERS: ClassVar[tuple[str, ...]] = (
        "institution",
        "student_name",
        "student_number",
        "program",
        "org_unit",
        "admission_date",
        "status",
        "year_level",
        "graduation_date",
        "degree_number",
        "birth_date",
        "gender",
        "nationality",
        "issue_date",
        "serial_number",
        "purpose",
        "copies",
    )

    def __init__(self, certificate_settings: CertificateSettings | None = None, pdf: Any = None) -> None:
        self._settings = certificate_settings
        self._pdf = pdf

    @property
    def settings(self) -> CertificateSettings:
        if self._settings is None:
            self._settings = CertificateSettings.load()
        return self._settings

    @property
    def pdf(self) -> Any:
        if self._pdf is None:
            from ninefruits.pdf import get_renderer

            self._pdf = get_renderer()
        return self._pdf

    # -- public API ---------------------------------------------------------------------------
    def render(self, issue: CertificateIssue) -> bytes:
        """The PDF bytes. Raises ``ninefruits.pdf.PdfRenderingError`` when Gotenberg fails."""
        return bytes(self.pdf.render(self.html(issue)))

    def html(self, issue: CertificateIssue) -> str:
        content = self.content(issue)
        with translation.override(issue.locale):
            return render_to_string(TEMPLATE, {"content": content, "title": content.title})

    def content(self, issue: CertificateIssue) -> CertificateContent:
        with session_context().system("certificate.render"), translation.override(issue.locale):
            return self._content(issue)

    def template(self, issue: CertificateIssue) -> CertificateTemplate:
        template = CertificateTemplate.objects.filter(
            certificate_type_id=issue.certificate_type_id, locale=issue.locale
        ).first()
        if template is None:
            raise ValidationError(
                {
                    "locale": gettext('This kind has no template for the language "%(locale)s".')
                    % {"locale": issue.locale}
                }
            )
        return template

    @classmethod
    def placeholder_help(cls) -> str:
        return ", ".join("{" + name + "}" for name in cls.PLACEHOLDERS)

    # -- internals ------------------------------------------------------------------------------
    def _content(self, issue: CertificateIssue) -> CertificateContent:
        from ninefruits.person.models import StudentRecord

        record = (
            StudentRecord.objects.select_related("person__nationality", "program", "org_unit")
            .filter(pk=issue.student_record_id)
            .get()
        )
        kind = issue.certificate_type
        template = self.template(issue)
        locale = issue.locale
        values = self._values(issue, record)

        def fill(text: str | None) -> str | None:
            if text is None:
                return None
            return _PLACEHOLDER.sub(lambda match: values.get(match.group(1), match.group(0)), text)

        terms = None
        cumulative_gpa = earned_credits = None
        if kind.has_grades:
            from ninefruits.grading.services.report import GradeReport

            terms = GradeReport().terms(record)
            latest = terms[-1].record if terms else None
            if latest is not None:
                cumulative_gpa = None if latest.cumulative_gpa is None else str(latest.cumulative_gpa)
                earned_credits = _number(latest.cumulative_earned_credits)

        url = verification_url(issue.verification_code)
        body = fill(template.body) or ""
        return CertificateContent(
            institution=values["institution"],
            title=fill(template.title) or "",
            facts=self._facts(issue, record, values),
            paragraphs=[part.strip() for part in _PARAGRAPH_BREAK.split(body) if part.strip()],
            footer=fill(template.footer),
            signer=template.signer or (self.settings.signer or {}).get(locale) or None,
            serial_number=issue.serial_number,
            issued_on=values["issue_date"],
            verification_url=url,
            qr_svg=qr_svg(url),
            photo_data_uri=self._photo(record.person) if kind.has_photo else None,
            terms=terms,
            cumulative_gpa=cumulative_gpa,
            earned_credits=earned_credits,
            locale=locale,
        )

    def _values(self, issue: CertificateIssue, record: Any) -> dict[str, str]:
        """Placeholder values in the active (the issue's) language."""
        from ninefruits.person.enums import Gender, StudentStatus

        locale = issue.locale

        def date(value: Any) -> str:
            # Original ``isoFormat('LL')`` in the template's language.
            return format_ll(value, locale)

        person = record.person
        return {
            "institution": institution_name(locale),
            "student_name": person.display_name(locale),
            "student_number": record.student_number,
            "program": str(record.program.name),
            "org_unit": str(record.org_unit.name),
            "admission_date": date(record.admission_date),
            "status": str(StudentStatus(record.status).label),
            "year_level": str(record.year_level),
            "graduation_date": date(record.graduation_date),
            "degree_number": str(record.degree_number or ""),
            "birth_date": date(person.birth_date),
            "gender": str(Gender(person.gender).label) if person.gender else "",
            "nationality": str(person.nationality.name) if person.nationality_id else "",
            "issue_date": date(institution_now(issue.issued_at).date()),
            "serial_number": issue.serial_number,
            "purpose": str(issue.purpose or ""),
            "copies": str(issue.copies),
        }

    @staticmethod
    def _facts(issue: CertificateIssue, record: Any, values: dict[str, str]) -> dict[str, str]:
        facts = {
            pgettext("certificate", "Name"): values["student_name"],
            gettext("Student number"): values["student_number"],
            gettext("Date of birth"): values["birth_date"],
            gettext("Gender"): values["gender"],
            gettext("Nationality"): values["nationality"],
            pgettext("certificate", "Program"): values["program"],
            pgettext("certificate", "Admitted"): values["admission_date"],
        }
        if issue.certificate_type.audience == CertificateAudience.GRADUATED or record.graduation_date is not None:
            facts[pgettext("certificate", "Graduated")] = values["graduation_date"]
        else:
            facts[pgettext("certificate", "Status")] = values["status"]
            facts[pgettext("certificate", "Year")] = values["year_level"]
        return {label: value for label, value in facts.items() if value != ""}

    @staticmethod
    def _photo(person: Any) -> str | None:
        from ninefruits.media.services import open_media

        media = person.get_first_media(person.PHOTO_COLLECTION)
        if media is None:
            return None
        try:
            with open_media(media) as handle:
                data = handle.read()
        except FileNotFoundError:
            return None
        return f"data:{media.mime_type};base64,{base64.b64encode(data).decode()}"
