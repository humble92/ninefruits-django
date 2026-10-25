"""Checks a verification code for anyone (original ``CertificateVerification``: the public page,
``certificate_verify`` and, from Phase 12, the verification API).

The issue is looked up in the system context (nobody is signed in, and row level security shows
an anonymous user nothing) by the unique code, and the result tells only what the paper already
shows: kind, serial number, issue date, the holder's masked name and number."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
from typing import Any

from django.utils import timezone

from ninefruits.certificate.enums import CertificateIssueStatus, VerificationReason
from ninefruits.certificate.models import CertificateIssue
from ninefruits.certificate.settings import CertificateSettings
from ninefruits.core.db import session_context

MAX_CODE_LENGTH = 40


@dataclass(frozen=True)
class VerificationResult:
    valid: bool
    reason: VerificationReason | None = None
    issue: CertificateIssue | None = None
    #: The holder's name with the middle masked (first and last character).
    holder: str | None = None
    #: The student number with all but the first four characters masked.
    student_number: str | None = None

    def as_dict(self) -> dict[str, Any]:
        """The verification JSON (Phase 12 API): nothing the paper does not show."""
        from ninefruits.certificate.services.serials import institution_now

        issue = self.issue
        return {
            "valid": self.valid,
            "reason": self.reason.value if self.reason is not None else None,
            "certificate": None
            if issue is None
            else {
                "type": issue.certificate_type.code,
                "type_name": issue.certificate_type.name_in(issue.locale),
                "locale": issue.locale,
                "serial_number": issue.serial_number,
                "issued_on": institution_now(issue.issued_at).date().isoformat(),
                "status": issue.status,
                "holder": self.holder,
                "student_number": self.student_number,
            },
        }


def mask_name(name: str) -> str:
    """``"홍길동"`` -> ``"홍*동"``, ``"Ji"`` -> ``"J*"`` (original ``maskName``)."""
    chars = list(name)
    if len(chars) <= 2:
        return (chars[0] if chars else "") + "*" * max(0, len(chars) - 1)
    return chars[0] + "*" * (len(chars) - 2) + chars[-1]


def mask_number(number: str) -> str:
    """``"202600123"`` -> ``"2026*****"`` (original ``maskNumber``)."""
    return number if len(number) <= 4 else number[:4] + "*" * (len(number) - 4)


class CertificateVerification:
    def __init__(self, settings: CertificateSettings | None = None) -> None:
        self._settings = settings

    @property
    def settings(self) -> CertificateSettings:
        if self._settings is None:
            self._settings = CertificateSettings.load()
        return self._settings

    def check(self, code: str) -> VerificationResult:
        code = (code or "").strip().upper()
        if code == "" or len(code) > MAX_CODE_LENGTH:
            return VerificationResult(False, VerificationReason.UNKNOWN)

        with session_context().system("certificate.verify"):
            issue = (
                CertificateIssue.objects.select_related("certificate_type", "student_record__person")
                .filter(verification_code=code)
                .first()
            )
        if issue is None:
            return VerificationResult(False, VerificationReason.UNKNOWN)
        if issue.status == CertificateIssueStatus.REVOKED:
            return self._result(False, VerificationReason.REVOKED, issue)
        days = self.settings.verification_valid_days
        if days > 0 and issue.issued_at + timedelta(days=days) < timezone.now():
            return self._result(False, VerificationReason.EXPIRED, issue)
        return self._result(True, None, issue)

    @staticmethod
    def _result(valid: bool, reason: VerificationReason | None, issue: CertificateIssue) -> VerificationResult:
        record = issue.student_record
        return VerificationResult(
            valid,
            reason,
            issue,
            holder=mask_name(record.person.display_name(issue.locale)),
            student_number=mask_number(record.student_number),
        )
