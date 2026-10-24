"""Person enums (original ``App\\Domain\\Person\\Enums``)."""

from __future__ import annotations

from django.db import models
from django.utils.translation import gettext_lazy as _
from django.utils.translation import pgettext_lazy


class StudentStatus(models.TextChoices):
    """Status of a student record (legacy SRALTERDEF / SR_ABSENT / SR_LEFT, and the move from
    SRREGISTRY to SGREGISTRY on graduation). Changed only through status changes."""

    ENROLLED = "enrolled", pgettext_lazy("people", "Enrolled")
    ON_LEAVE = "on_leave", _("On leave")
    WITHDRAWN = "withdrawn", pgettext_lazy("people", "Withdrawn")
    DISMISSED = "dismissed", _("Dismissed")
    GRADUATED = "graduated", pgettext_lazy("people", "Graduated")

    def is_active(self) -> bool:
        """The record is current: the student is enrolled or on leave."""
        return self in (StudentStatus.ENROLLED, StudentStatus.ON_LEAVE)

    @classmethod
    def active(cls) -> list[StudentStatus]:
        return [cls.ENROLLED, cls.ON_LEAVE]


class StatusChangeStatus(models.TextChoices):
    REQUESTED = "requested", pgettext_lazy("people", "Requested")
    APPROVED = "approved", _("Approved")
    REJECTED = "rejected", _("Rejected")
    CANCELLED = "cancelled", pgettext_lazy("people", "Cancelled")


class AdditionalProgramRequestStatus(models.TextChoices):
    REQUESTED = "requested", pgettext_lazy("people", "Pending")
    APPROVED = "approved", _("Approved")
    REJECTED = "rejected", _("Rejected")
    CANCELLED = "cancelled", pgettext_lazy("people", "Cancelled")


class AdditionalProgramRole(models.TextChoices):
    """Programs a student record follows besides its primary program (double major, minor)."""

    SECOND_MAJOR = "second_major", _("Second major")
    MINOR = "minor", _("Minor")


class AdvisorRole(models.TextChoices):
    PRIMARY = "primary", _("Primary advisor")
    CO_ADVISOR = "co_advisor", _("Co-advisor")


class EmploymentType(models.TextChoices):
    FULL_TIME = "full_time", _("Full-time")
    PART_TIME = "part_time", _("Part-time")
    ADJUNCT = "adjunct", _("Adjunct")
    VISITING = "visiting", _("Visiting")
    EMERITUS = "emeritus", _("Emeritus")


class Gender(models.TextChoices):
    FEMALE = "female", _("Female")
    MALE = "male", _("Male")
    OTHER = "other", _("Other")
    UNDISCLOSED = "undisclosed", _("Not disclosed")


class GuardianRelationship(models.TextChoices):
    FATHER = "father", _("Father")
    MOTHER = "mother", _("Mother")
    GUARDIAN = "guardian", _("Guardian")
    SPOUSE = "spouse", _("Spouse")
    SIBLING = "sibling", _("Sibling")
    GRANDPARENT = "grandparent", _("Grandparent")
    OTHER = "other", _("Other")
