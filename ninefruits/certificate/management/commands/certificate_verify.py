"""Checks a certificate verification code as the public page does (original
``certificate:verify``). Read only: no audit. Exit code 2 when the code is not valid."""

from __future__ import annotations

from typing import Any

from django.core.management.base import CommandParser

from ninefruits.certificate.services import CertificateVerification, institution_now
from ninefruits.core.commands import StatusCommand


class Command(StatusCommand):
    help = "Check a certificate verification code, as the public page does"

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument("code", help="Verification code printed on the certificate")

    def handle(self, *args: Any, **options: Any) -> int:
        result = CertificateVerification().check(str(options["code"]))
        issue = result.issue
        if issue is not None:
            self.detail("Type", f"{issue.certificate_type.code} ({issue.locale})")
            self.detail("Serial", issue.serial_number)
            self.detail("Issued", institution_now(issue.issued_at).date().isoformat())
            self.detail("Holder", f"{result.holder} {result.student_number}")
        if result.valid:
            self.info("Valid.")
            return self.SUCCESS
        reason = result.reason.value if result.reason is not None else "unknown"
        self.warn(f"Not valid: {reason}.")
        return self.PROBLEMS_FOUND
