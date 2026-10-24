"""Examination sessions and registrations (original ``App\\Models\\Assessment\\AssessmentSession``
and ``AssessmentRegistration``; legacy CET_HISTORY and CET.APPLYCHECK).

A session is one sitting of a kind: the date (one per kind and date), the registration window,
the capacity, a pass score overriding the kind's and when its results were published to the
students. Sessions are configuration; a session with registrations or results cannot be deleted
(``on_delete=PROTECT``, the database restricts too: legacy deletions orphaned the rows).

A registration is a student's place in a session. Cancelled rows stay and are reactivated when
the student registers again. Staff see those of the student records they can see; students their
own (row level security ``assessment_registrations_record_select``)."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any, Self

from django.conf import settings
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.utils.translation import pgettext_lazy

from ninefruits.assessment.enums import AssessmentRegistrationStatus
from ninefruits.core.models import TimeStampedModel, VisibleQuerySet

from .types import AssessmentType


class AssessmentSessionQuerySet(VisibleQuerySet):
    def open_for_registration(self, at: datetime | None = None) -> Self:
        """Sessions whose registration window contains ``at`` (now by default)."""
        at = at or timezone.now()
        return self.filter(registration_opens_at__lte=at, registration_closes_at__gt=at)


class AssessmentSession(TimeStampedModel):
    assessment_type = models.ForeignKey(
        AssessmentType,
        on_delete=models.PROTECT,
        related_name="sessions",
        verbose_name=pgettext_lazy("assessment", "Kind"),
    )
    held_date = models.DateField(pgettext_lazy("assessment", "Date"))
    venue = models.CharField(_("Venue"), max_length=120, null=True, blank=True)
    registration_opens_at = models.DateTimeField(_("Registration opens"), null=True, blank=True)
    registration_closes_at = models.DateTimeField(_("Registration closes"), null=True, blank=True)
    capacity = models.IntegerField(pgettext_lazy("assessment", "Capacity"), null=True, blank=True)
    #: Overrides the kind's pass score for this session (legacy CET_CUTLINE).
    pass_score = models.DecimalField(
        _("Pass score"),
        max_digits=6,
        decimal_places=1,
        null=True,
        blank=True,
        help_text=_(
            "Leave empty to use the kind's pass score. Changing it before publication judges every entered "
            "result again; after publication it is fixed."
        ),
    )
    results_published_at = models.DateTimeField(pgettext_lazy("assessment", "Results published"), null=True, blank=True)

    objects = AssessmentSessionQuerySet.as_manager()

    class Meta:
        db_table = "assessment_sessions"
        ordering = ["-held_date", "-id"]
        verbose_name = _("Examination session")
        verbose_name_plural = _("Examination sessions")
        constraints = [
            models.UniqueConstraint(
                fields=["assessment_type", "held_date"], name="assessment_sessions_assessment_type_id_held_date_unique"
            ),
        ]

    def __str__(self) -> str:
        return self.label()

    def __repr__(self) -> str:
        return f"<AssessmentSession {self.pk} type={self.assessment_type_id} {self.held_date}>"

    def label(self) -> str:
        """``English comprehensive examination 2026-05-15`` in the active language."""
        return f"{self.assessment_type.name} {self.held_date.isoformat()}"

    @property
    def is_published(self) -> bool:
        return self.results_published_at is not None

    def is_open_for_registration(self, at: datetime | None = None) -> bool:
        """Students may register now: both window ends set and around now."""
        at = at or timezone.now()
        return (
            self.registration_opens_at is not None
            and self.registration_closes_at is not None
            and self.registration_opens_at <= at < self.registration_closes_at
        )

    def effective_pass_score(self) -> Decimal | None:
        """The pass score in force: the session's override, else the kind's (original
        ``passScore``)."""
        return self.pass_score if self.pass_score is not None else self.assessment_type.pass_score

    def is_past(self) -> bool:
        return self.held_date < timezone.localdate()


class AssessmentRegistrationQuerySet(VisibleQuerySet):
    def active(self) -> Self:
        """Registered or absent: holding a seat."""
        return self.filter(status__in=AssessmentRegistrationStatus.active())

    def visible_to(self, user: Any) -> Self:
        """Registrations of student records the user can see (RLS
        ``assessment_registrations_record_select``): staff by their scope, students their own."""
        from ninefruits.person.models import StudentRecord

        if user is None or not getattr(user, "is_authenticated", False):
            return self.none()
        return self.filter(student_record_id__in=StudentRecord.objects.visible_to(user).values("pk"))


class AssessmentRegistration(TimeStampedModel):
    session = models.ForeignKey(
        AssessmentSession,
        on_delete=models.PROTECT,
        related_name="registrations",
        db_column="assessment_session_id",
        verbose_name=_("Examination session"),
    )
    student_record = models.ForeignKey(
        "person.StudentRecord",
        on_delete=models.PROTECT,
        related_name="assessment_registrations",
        verbose_name=_("student record"),
    )
    status = models.CharField(
        pgettext_lazy("registration", "Status"),
        max_length=16,
        choices=AssessmentRegistrationStatus.choices,
        default=AssessmentRegistrationStatus.REGISTERED,
    )
    registered_at = models.DateTimeField(pgettext_lazy("assessment.fields", "Registered"))
    #: Null when the student registered themselves.
    registered_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )
    cancelled_at = models.DateTimeField(null=True, blank=True)
    cancel_reason = models.TextField(pgettext_lazy("common", "Reason"), null=True, blank=True)

    objects = AssessmentRegistrationQuerySet.as_manager()

    class Meta:
        db_table = "assessment_registrations"
        ordering = ["registered_at", "id"]
        verbose_name = _("Registrants")
        verbose_name_plural = _("Registrants")
        constraints = [
            models.UniqueConstraint(
                fields=["session", "student_record"],
                name="assessment_registrations_assessment_session_id_student_record_i",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.session_id}: {self.student_record_id}"

    def __repr__(self) -> str:
        return (
            f"<AssessmentRegistration {self.pk} session={self.session_id} "
            f"record={self.student_record_id} {self.status}>"
        )

    @property
    def assessment_session_id(self) -> int:
        return int(self.session_id)

    @property
    def is_cancelled(self) -> bool:
        return self.status == AssessmentRegistrationStatus.CANCELLED
