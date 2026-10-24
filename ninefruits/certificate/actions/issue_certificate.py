"""Issues, re-renders and revokes certificates (original ``IssueCertificate``, ADR 0013).

Staff only (porting-plan 17.5): a ledger row with a serial number and verification code, the PDF
rendered and stored as a file of the issue, its SHA-256 checksum kept. Holds that block
certificates refuse. Revocation changes the status only; the row and the file stay."""

from __future__ import annotations

import hashlib
import secrets
import string
from typing import Any

from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.utils import timezone
from django.utils.translation import gettext

from ninefruits.audit.logger import audit
from ninefruits.certificate.enums import CertificateAudience, CertificateIssueStatus
from ninefruits.certificate.models import CertificateIssue, CertificateTemplate, CertificateType
from ninefruits.certificate.services.renderer import CertificateRenderer
from ninefruits.certificate.services.serials import CertificateSerialGenerator
from ninefruits.core.db import session_context
from ninefruits.security.enums import Permission

CODE_ALPHABET = string.ascii_uppercase + string.digits
CODE_LENGTH = 20
MAX_COPIES = 20


def verification_code() -> str:
    """20 random upper case letters and digits (original ``Str::upper(Str::random(20))``)."""
    return "".join(secrets.choice(CODE_ALPHABET) for _ in range(CODE_LENGTH))


def can_issue(user: Any) -> bool:
    """``certificates.issue`` granted globally. The database policy
    (``certificate_issues_staff_write``) accepts only a global grant; the student record scope
    comes from the record's own visibility. (The original let a scoped grant through and the
    database then refused the row.)"""
    from ninefruits.security.services.authorization import authorization

    if not getattr(user, "is_authenticated", False) or not user.has_perm(Permission.CERTIFICATES_ISSUE):
        return False
    return bool(authorization().scope_for(user, Permission.CERTIFICATES_ISSUE).is_global)


class IssueCertificate:
    def __init__(
        self, serials: CertificateSerialGenerator | None = None, renderer: CertificateRenderer | None = None
    ) -> None:
        self.serials = serials or CertificateSerialGenerator()
        self.renderer = renderer or CertificateRenderer()

    def handle(
        self,
        record: Any,
        certificate_type: CertificateType,
        locale: str,
        staff: Any,
        purpose: str | None = None,
        copies: int = 1,
    ) -> CertificateIssue:
        if not can_issue(staff) or not record.is_visible_to(staff):
            raise PermissionDenied
        if not certificate_type.is_active:
            raise ValidationError({"certificate_type": gettext("This kind of certificate is not issued any more.")})
        self._check_audience(record, certificate_type)
        if self._blocking_hold_exists(record):
            raise ValidationError(
                {"student_record": gettext("A hold blocks certificates for this student. Lift it first.")}
            )
        if not CertificateTemplate.objects.filter(certificate_type=certificate_type, locale=locale).exists():
            raise ValidationError(
                {"locale": gettext('This kind has no template for the language "%(locale)s".') % {"locale": locale}}
            )

        purpose = purpose.strip() if purpose and purpose.strip() else None
        now = timezone.now().replace(microsecond=0)
        # The number is taken on its own: a failed issue skips it (uniqueness over continuity).
        issue = CertificateIssue(
            student_record=record,
            certificate_type=certificate_type,
            locale=locale,
            serial_number=self.serials.next(certificate_type.code, now),
            verification_code=verification_code(),
            purpose=purpose,
            copies=max(1, min(MAX_COPIES, int(copies))),
            status=CertificateIssueStatus.ISSUED,
            issued_at=now,
            issued_by=staff,
        )
        # Rendered before anything is stored: when the PDF service fails, nothing is issued.
        pdf = self.renderer.render(issue)
        with transaction.atomic():
            issue.save()
            self._store_pdf(issue, pdf)
            audit(
                "certificate.issued",
                issue,
                reason=purpose,
                properties={
                    "student_number": record.student_number,
                    "type": certificate_type.code,
                    "locale": locale,
                    "serial": issue.serial_number,
                    "copies": issue.copies,
                },
                causer=staff,
            )
        return issue

    def rerender(self, issue: CertificateIssue, staff: Any = None) -> CertificateIssue:
        """Renders the PDF again from the current data and template and replaces the stored file
        (e.g. after a template fix); the serial number and code stay. ``staff`` is ``None`` for
        the command."""
        if staff is not None and not can_issue(staff):
            raise PermissionDenied
        pdf = self.renderer.render(issue)
        with transaction.atomic():
            self._store_pdf(issue, pdf)
            audit("certificate.rerendered", issue, properties={"serial": issue.serial_number}, causer=staff)
        return issue

    def revoke(self, issue: CertificateIssue, staff: Any, reason: str) -> CertificateIssue:
        if not can_issue(staff):
            raise PermissionDenied
        if issue.status == CertificateIssueStatus.REVOKED:
            raise ValidationError({"status": gettext("This certificate is already revoked.")})
        if not (reason or "").strip():
            raise ValidationError({"reason": gettext("Enter a reason.")})
        with transaction.atomic():
            issue.status = CertificateIssueStatus.REVOKED
            issue.revoked_at = timezone.now().replace(microsecond=0)
            issue.revoked_by = staff
            issue.revocation_reason = reason
            issue.save(update_fields=["status", "revoked_at", "revoked_by", "revocation_reason", "updated_at"])
            audit("certificate.revoked", issue, reason=reason, properties={"serial": issue.serial_number}, causer=staff)
        return issue

    # -- internals ------------------------------------------------------------------------------
    @staticmethod
    def _check_audience(record: Any, certificate_type: CertificateType) -> None:
        from ninefruits.person.enums import StudentStatus

        graduated = record.status == StudentStatus.GRADUATED
        audience = CertificateAudience(certificate_type.audience)
        allowed = {
            CertificateAudience.ANY: True,
            CertificateAudience.ENROLLED: not graduated,
            CertificateAudience.GRADUATED: graduated,
        }[audience]
        if not allowed:
            raise ValidationError(
                {
                    "certificate_type": gettext("This certificate is only for: %(audience)s.")
                    % {"audience": audience.label}
                }
            )

    @staticmethod
    def _blocking_hold_exists(record: Any) -> bool:
        """Checked in the system context: the issuer's row level security may hide holds, and a
        hidden hold must still block."""
        from ninefruits.registration.models import RegistrationHold

        with session_context().system("certificate.issue"):
            return (
                RegistrationHold.objects.filter(student_record_id=record.pk, blocks_certificates=True)
                .in_force()
                .exists()
            )

    @staticmethod
    def _store_pdf(issue: CertificateIssue, pdf: bytes) -> None:
        from ninefruits.media.services import add_media_from_bytes

        add_media_from_bytes(issue, pdf, f"{issue.serial_number}.pdf", CertificateIssue.PDF_COLLECTION)
        issue.pdf_checksum = hashlib.sha256(pdf).hexdigest()
        issue.save(update_fields=["pdf_checksum", "updated_at"])
