"""Registration enums (original ``App\\Domain\\Registration\\Enums``). ``GradeStatus`` is the
grading enum (``ninefruits.grading.enums``), re-exported for the registration code."""

from __future__ import annotations

from django.db import models
from django.utils.translation import gettext_lazy as _
from django.utils.translation import pgettext_lazy

from ninefruits.grading.enums import GradeStatus as _GradeStatus


class AttemptAction(models.TextChoices):
    ENROLL = "enroll", pgettext_lazy("registration", "Register")
    DROP = "drop", pgettext_lazy("registration.attempt_actions", "Drop")
    WITHDRAW = "withdraw", pgettext_lazy("registration.attempt_actions", "Withdraw")
    WAITLIST = "waitlist", pgettext_lazy("registration.attempt_actions", "Waitlist")
    PROMOTE = "promote", _("Waitlist promotion")
    CART = "cart", _("Cart")


class AttemptOutcome(models.TextChoices):
    SUCCEEDED = "succeeded", _("Succeeded")
    WAITLISTED = "waitlisted", _("Waitlisted")
    REFUSED = "refused", _("Refused")


class EnrollmentSource(models.TextChoices):
    STUDENT = "student", _("Student")
    STAFF = "staff", _("Staff")
    WAITLIST = "waitlist", pgettext_lazy("registration.enrollment_sources", "Waitlist")
    IMPORT = "import", _("Import")


class EnrollmentStatus(models.TextChoices):
    """Explicit status instead of the legacy "grade is NULL" convention (porting-plan 10.3).
    Rows are never deleted: a drop keeps the row as dropped."""

    ENROLLED = "enrolled", pgettext_lazy("registration.enrollment_statuses", "Registered")
    DROPPED = "dropped", _("Dropped")
    WITHDRAWN = "withdrawn", pgettext_lazy("registration", "Withdrawn")
    COMPLETED = "completed", _("Completed")


#: Moved to ``ninefruits.grading.enums`` in Phase 6 (the original Grading enum); kept here as an
#: alias for the registration code that reads the enrollment's grade column.
GradeStatus = _GradeStatus


class HoldType(models.TextChoices):
    """Kinds of holds (legacy SRDENY had one kind). "unregistered": the term fee is not paid;
    there is no tuition module, so staff enter these by hand or CSV (porting-plan 4.2)."""

    UNREGISTERED = "unregistered", _("Not registered for the term")
    FINANCIAL = "financial", _("Financial")
    ACADEMIC = "academic", pgettext_lazy("registration", "Academic")
    ADMINISTRATIVE = "administrative", _("Administrative")
    OTHER = "other", _("Other")


class HoldSource(models.TextChoices):
    """Where a hold came from (``registration_holds_source_check``)."""

    MANUAL = "manual", "manual"
    IMPORT = "import", "import"
    SYSTEM = "system", "system"


class RuleCode(models.TextChoices):
    """Registration rules (porting-plan 10.6). The catalog is code; each term's rule set says per
    rule: enabled, block or warn, override allowed, parameters."""

    #: An open registration or add/drop window for the student (always on).
    WINDOW = "window", pgettext_lazy("registration.rules.window", "Registration period")
    #: The section is published (always on).
    SECTION_OPEN = "section_open", _("Section open")
    HOLD = "hold", _("Holds")
    STUDENT_STATUS = "student_status", _("Student status")
    ELIGIBILITY = "eligibility", _("Section eligibility")
    DUPLICATE_COURSE = "duplicate_course", _("Same course twice")
    TIME_CONFLICT = "time_conflict", _("Time conflict")
    CREDIT_LIMIT = "credit_limit", _("Credit limit")
    REQUISITES = "requisites", _("Prerequisites")
    REPEAT_COURSE = "repeat_course", _("Retakes")
    #: A seat is free (not a configurable rule: seats are taken atomically, reported here).
    CAPACITY = "capacity", _("Seats")

    @property
    def description(self) -> str:
        return str(_RULE_DESCRIPTIONS[self])

    def is_core(self) -> bool:
        """Rules a rule set cannot switch off or soften (staff can still waive them)."""
        return self in (RuleCode.WINDOW, RuleCode.SECTION_OPEN, RuleCode.CAPACITY)

    @classmethod
    def overridable(cls) -> list[RuleCode]:
        """Rules an override can pass: everything except the section state and seats."""
        return [code for code in cls if not code.is_core() or code == cls.WINDOW]


_RULE_DESCRIPTIONS = {
    RuleCode.WINDOW: _("A registration, add/drop or withdrawal period must be open for the student."),
    RuleCode.SECTION_OPEN: _("The section must be published."),
    RuleCode.HOLD: _("Students with a hold that blocks registration cannot register."),
    RuleCode.STUDENT_STATUS: _("Only students with the chosen statuses may register."),
    RuleCode.ELIGIBILITY: _("The student must match the section's eligibility and not its exclusions."),
    RuleCode.DUPLICATE_COURSE: _("A course can be registered only once per term."),
    RuleCode.TIME_CONFLICT: _("Meeting times must not overlap with other registered sections."),
    RuleCode.CREDIT_LIMIT: _("Total credits must not exceed the credit limit that applies to the student."),
    RuleCode.REQUISITES: _(
        "Prerequisites must be passed (equivalent courses count); corequisites may be taken in the same term."
    ),
    RuleCode.REPEAT_COURSE: _("Whether and how often a passed course may be taken again."),
    RuleCode.CAPACITY: _("A seat must be free (reserved seats count only for their students until released)."),
}


class RuleSeverity(models.TextChoices):
    BLOCK = "block", _("Block")
    WARN = "warn", _("Warn only")


class WaitlistStatus(models.TextChoices):
    WAITING = "waiting", pgettext_lazy("registration", "Waiting")
    PROMOTED = "promoted", pgettext_lazy("registration.waitlist_statuses", "Registered")
    REMOVED = "removed", _("Removed")
    EXPIRED = "expired", pgettext_lazy("registration", "Expired")
