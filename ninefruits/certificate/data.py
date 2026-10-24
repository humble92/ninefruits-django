"""Value objects of the certificates (original ``App\\Domain\\Certificate\\Data``)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class CertificateContent:
    """A certificate's rendered wording and data for the PDF template."""

    institution: str
    title: str
    #: label -> value, printed as a table above the body
    facts: dict[str, str]
    paragraphs: list[str]
    footer: str | None
    signer: str | None
    serial_number: str
    issued_on: str
    verification_url: str
    qr_svg: str
    photo_data_uri: str | None = None
    #: oldest first, only for kinds that include grades (``grading.services.report.TermGrades``)
    terms: list[Any] | None = None
    cumulative_gpa: str | None = None
    earned_credits: str | None = None
    locale: str = "en"
