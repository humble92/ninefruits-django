"""Admission enums (original ``App\\Domain\\Admission\\Enums``)."""

from __future__ import annotations

from django.db import models
from django.utils.translation import gettext_lazy as _
from django.utils.translation import pgettext_lazy


class ApplicationStatus(models.TextChoices):
    """draft -> submitted -> under_review -> admitted | rejected; admitted -> confirmed (the
    applicant accepts, then matriculation creates the student record) or withdrawn (declined).
    Applicants may withdraw at any point before matriculation. Drafts left in a closed cycle
    become expired (ADR 0008)."""

    DRAFT = "draft", pgettext_lazy("admissions", "Draft")
    SUBMITTED = "submitted", pgettext_lazy("admissions.application_statuses", "Submitted")
    UNDER_REVIEW = "under_review", _("Under review")
    ADMITTED = "admitted", pgettext_lazy("admissions", "Admitted")
    REJECTED = "rejected", _("Not admitted")
    CONFIRMED = "confirmed", _("Enrollment confirmed")
    WITHDRAWN = "withdrawn", pgettext_lazy("admissions", "Withdrawn")
    EXPIRED = "expired", pgettext_lazy("admissions", "Expired")

    def is_open(self) -> bool:
        """Not closed: blocks another application to the same cycle."""
        return self not in (ApplicationStatus.WITHDRAWN, ApplicationStatus.REJECTED, ApplicationStatus.EXPIRED)

    def is_awaiting_decision(self) -> bool:
        """Waiting for a staff decision."""
        return self in (ApplicationStatus.SUBMITTED, ApplicationStatus.UNDER_REVIEW)

    def is_decided(self) -> bool:
        return self in (ApplicationStatus.ADMITTED, ApplicationStatus.REJECTED)

    @classmethod
    def open_values(cls) -> list[str]:
        return [status.value for status in cls if status.is_open()]
