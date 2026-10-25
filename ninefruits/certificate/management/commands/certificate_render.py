"""Renders an issued certificate's PDF again from the current data and template, keeping its
number and code (original ``certificate:render``; the ledger's "Render again")."""

from __future__ import annotations

from typing import Any

from django.core.management.base import CommandParser

from ninefruits.certificate.actions import IssueCertificate
from ninefruits.certificate.models import CertificateIssue
from ninefruits.core.commands import AuditedCommand
from ninefruits.pdf import PdfRenderingError


class Command(AuditedCommand):
    help = "Render an issued certificate's PDF again from the current data and template, keeping its number and code"

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument("issue", help="Serial number of the issue")
        parser.add_argument("--reason", help="Why (required)")

    def handle(self, *args: Any, **options: Any) -> int:  # type: ignore[override]  # exit code (StatusCommand)
        if not (options.get("reason") or "").strip():
            self.error("--reason is required.")
            return self.FAILURE
        issue = CertificateIssue.objects.filter(serial_number=str(options["issue"])).first()
        if issue is None:
            self.error("Unknown serial number.")
            return self.FAILURE
        try:
            IssueCertificate().rerender(issue, self.actor())
        except PdfRenderingError as error:
            self.error(f"The PDF could not be created: {error}")
            return self.FAILURE
        self.record_result({"serial": issue.serial_number, "checksum": issue.pdf_checksum})
        self.info(f"Rendered {issue.serial_number} (sha256 {issue.pdf_checksum}).")
        return self.SUCCESS
