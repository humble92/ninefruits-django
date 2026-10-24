"""Enrollments, waitlist entries, cart items and the attempt log (original
``App\\Models\\Registration\\{Enrollment,WaitlistEntry,CartItem,RegistrationAttempt}``, ADR 0010).

``visible_to`` mirrors the row level security policies of ``db/sql/policies/registration.sql``
(and the grade viewing policy of ``grading.sql``): what a user may read the database also returns."""

from __future__ import annotations

from typing import Any, Self

from django.conf import settings
from django.db import models
from django.db.models import Q
from django.utils.translation import gettext_lazy as _
from django.utils.translation import pgettext_lazy

from ninefruits.core.models import TimeStampedModel, VisibleQuerySet
from ninefruits.registration.enums import (
    AttemptAction,
    AttemptOutcome,
    EnrollmentSource,
    EnrollmentStatus,
    GradeStatus,
    RuleCode,
    WaitlistStatus,
)
from ninefruits.security.enums import Permission


def _scope(user: Any, permission: Permission) -> Any:
    from ninefruits.security.services.authorization import PermissionScope, authorization

    if user is None or not getattr(user, "is_authenticated", False):
        return PermissionScope.none()
    return authorization().scope_for(user, permission)


def section_scope_condition(user: Any, *permissions: Permission, prefix: str = "section__") -> Q | None:
    """Rows of sections offered by units in the user's scope for any of the permissions (RLS:
    ``util.has_permission`` or ``s.org_unit_id = ANY(util.permission_org_unit_ids(...))``).
    ``None`` means every row (a global grant)."""
    units: list[int] = []
    for permission in permissions:
        scope = _scope(user, permission)
        if scope.is_global:
            return None
        units.extend(scope.org_unit_ids)
    return Q(**{f"{prefix}org_unit_id__in": list(dict.fromkeys(units))}) if units else Q(pk__in=[])


def visible_record_ids(user: Any) -> Any:
    from ninefruits.person.models import StudentRecord

    return StudentRecord.objects.visible_to(user).values("pk")


def taught_section_ids(user: Any) -> Any:
    from ninefruits.offering.models import Section

    return Section.objects.taught_by(getattr(user, "person_id", None)).values("pk")


class EnrollmentQuerySet(VisibleQuerySet):
    def active(self) -> Self:
        return self.filter(status=EnrollmentStatus.ENROLLED)

    def holding_seat(self) -> Self:
        """Rows that take a seat (registered or completed)."""
        return self.filter(status__in=[EnrollmentStatus.ENROLLED, EnrollmentStatus.COMPLETED])

    def visible_to(self, user: Any) -> Self:
        """Enrollments of records the user can see, of sections in their ``enrollments.view`` or
        ``registration.manage`` scope (or ``grades.view``), and of sections they teach."""
        section_condition = section_scope_condition(
            user, Permission.ENROLLMENTS_VIEW, Permission.REGISTRATION_MANAGE, Permission.GRADES_VIEW
        )
        if section_condition is None:
            return self
        condition = Q(student_record_id__in=visible_record_ids(user)) | section_condition
        if getattr(user, "person_id", None) is not None:
            condition |= Q(section_id__in=taught_section_ids(user))
        return self.filter(condition)


class Enrollment(TimeStampedModel):
    """A student record in a section (legacy SSCORE): registration, then the grade (entered,
    submitted, finalized in Phase 6; a finalized grade changes only through a grade change
    request). Credits, version and category are a snapshot of the course as taken."""

    student_record = models.ForeignKey(
        "person.StudentRecord", on_delete=models.RESTRICT, related_name="enrollments", verbose_name=_("student record")
    )
    section = models.ForeignKey(
        "offering.Section",
        on_delete=models.RESTRICT,
        related_name="enrollments",
        verbose_name=pgettext_lazy("offering", "Section"),
    )
    term = models.ForeignKey("term.Term", on_delete=models.RESTRICT, related_name="enrollments")
    course = models.ForeignKey("curriculum.Course", on_delete=models.RESTRICT, related_name="enrollments")
    version = models.ForeignKey(
        "curriculum.CourseVersion", on_delete=models.RESTRICT, related_name="enrollments", db_column="course_version_id"
    )
    credits = models.DecimalField(pgettext_lazy("registration", "Credits"), max_digits=4, decimal_places=1)
    category = models.ForeignKey(
        "curriculum.CourseCategory",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
        db_column="course_category_id",
    )
    counts_toward_credit_limit = models.BooleanField(default=True)
    status = models.CharField(
        pgettext_lazy("registration", "Status"),
        max_length=16,
        choices=EnrollmentStatus.choices,
        default=EnrollmentStatus.ENROLLED,
    )
    seat_group = models.ForeignKey(
        "offering.SectionSeatGroup", on_delete=models.SET_NULL, null=True, blank=True, related_name="enrollments"
    )
    is_retake = models.BooleanField(_("Retake"), default=False)
    repeats_enrollment = models.ForeignKey(
        "self", on_delete=models.SET_NULL, null=True, blank=True, related_name="retakes"
    )
    source = models.CharField(
        pgettext_lazy("registration", "Source"),
        max_length=16,
        choices=EnrollmentSource.choices,
        default=EnrollmentSource.STUDENT,
    )
    enrolled_at = models.DateTimeField(_("Registered at"))
    dropped_at = models.DateTimeField(null=True, blank=True)
    withdrawn_at = models.DateTimeField(null=True, blank=True)
    changed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )
    grade_status = models.CharField(max_length=16, choices=GradeStatus.choices, default=GradeStatus.NONE)
    grade_code = models.CharField(max_length=8, null=True, blank=True)
    is_passed = models.BooleanField(null=True, blank=True)
    grade_scale = models.ForeignKey(
        "grading.GradeScale", on_delete=models.RESTRICT, null=True, blank=True, related_name="+"
    )
    score = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    grade_points = models.DecimalField(max_digits=4, decimal_places=2, null=True, blank=True)
    counts_in_gpa = models.BooleanField(null=True, blank=True)
    grade_entered_at = models.DateTimeField(null=True, blank=True)
    grade_entered_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )
    grade_submitted_at = models.DateTimeField(null=True, blank=True)
    grade_submitted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )
    grade_finalized_at = models.DateTimeField(null=True, blank=True)
    grade_finalized_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )

    objects = EnrollmentQuerySet.as_manager()

    class Meta:
        db_table = "enrollments"
        ordering = ["-enrolled_at", "-id"]
        verbose_name = _("registration")
        verbose_name_plural = _("registrations")
        constraints = [
            # Partial unique indexes of the schema (documentation; the database has them).
            models.UniqueConstraint(
                fields=["student_record", "term", "course"],
                condition=Q(status="enrolled"),
                name="enrollments_active_course_unique",
            ),
            models.UniqueConstraint(
                fields=["student_record", "section"],
                condition=Q(status__in=["enrolled", "completed"]),
                name="enrollments_active_section_unique",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.student_record_id}:{self.section_id}"

    def __repr__(self) -> str:
        return f"<Enrollment {self.pk} record={self.student_record_id} section={self.section_id}>"

    @property
    def course_version_id(self) -> int | None:
        return self.version_id

    @property
    def course_category_id(self) -> int | None:
        return self.category_id

    @property
    def enrollment_status(self) -> EnrollmentStatus:
        return EnrollmentStatus(self.status)

    @property
    def is_active(self) -> bool:
        return self.status == EnrollmentStatus.ENROLLED

    def display_grade(self) -> str | None:
        """The grade to show: the grade code, W for a withdrawal."""
        return "W" if self.status == EnrollmentStatus.WITHDRAWN else self.grade_code


class WaitlistEntryQuerySet(VisibleQuerySet):
    def waiting(self) -> Self:
        return self.filter(status=WaitlistStatus.WAITING)

    def visible_to(self, user: Any) -> Self:
        """The record's own entries, and entries of sections in the user's ``registration.manage``
        scope (RLS ``waitlist_entries_*``)."""
        section_condition = section_scope_condition(user, Permission.REGISTRATION_MANAGE)
        if section_condition is None:
            return self
        return self.filter(Q(student_record_id__in=visible_record_ids(user)) | section_condition)


class WaitlistEntry(TimeStampedModel):
    """A student waiting for a seat. Entries are served in request order; each promotion checks
    the registration rules again."""

    section = models.ForeignKey("offering.Section", on_delete=models.CASCADE, related_name="waitlist_entries")
    student_record = models.ForeignKey(
        "person.StudentRecord", on_delete=models.CASCADE, related_name="waitlist_entries"
    )
    status = models.CharField(
        pgettext_lazy("registration", "Status"),
        max_length=16,
        choices=WaitlistStatus.choices,
        default=WaitlistStatus.WAITING,
    )
    requested_at = models.DateTimeField(pgettext_lazy("registration", "Requested"))
    requested_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )
    resolved_at = models.DateTimeField(null=True, blank=True)
    enrollment = models.ForeignKey(
        Enrollment, on_delete=models.SET_NULL, null=True, blank=True, related_name="waitlist_entries"
    )
    outcome_note = models.TextField(pgettext_lazy("registration", "Note"), null=True, blank=True)

    objects = WaitlistEntryQuerySet.as_manager()

    class Meta:
        db_table = "waitlist_entries"
        ordering = ["requested_at", "id"]
        verbose_name = pgettext_lazy("registration.resources.waitlist", "Waitlist")
        verbose_name_plural = pgettext_lazy("registration.resources.waitlist", "Waitlist")
        constraints = [
            models.UniqueConstraint(
                fields=["section", "student_record"],
                condition=Q(status="waiting"),
                name="waitlist_entries_single_waiting_unique",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.section_id}:{self.student_record_id}"

    def __repr__(self) -> str:
        return f"<WaitlistEntry {self.pk} section={self.section_id} record={self.student_record_id}>"

    def position(self) -> int:
        """Position among waiting entries of the section (1 = next)."""
        return WaitlistEntry.objects.filter(
            section_id=self.section_id, status=WaitlistStatus.WAITING, requested_at__lte=self.requested_at
        ).count()


class CartItemQuerySet(VisibleQuerySet):
    def visible_to(self, user: Any) -> Self:
        """The cart of records the user can see (RLS ``cart_items_record_select``)."""
        return self.filter(student_record_id__in=visible_record_ids(user))


class CartItem(TimeStampedModel):
    """A section a student plans to register for. The cart is checked in advance and submitted
    at once when registration opens (porting-plan 10.7)."""

    student_record = models.ForeignKey("person.StudentRecord", on_delete=models.CASCADE, related_name="cart_items")
    term = models.ForeignKey("term.Term", on_delete=models.CASCADE, related_name="+")
    section = models.ForeignKey("offering.Section", on_delete=models.CASCADE, related_name="cart_items")

    objects = CartItemQuerySet.as_manager()

    class Meta:
        db_table = "cart_items"
        ordering = ["id"]
        verbose_name = _("Cart")
        verbose_name_plural = _("Cart")
        constraints = [
            models.UniqueConstraint(
                fields=["student_record", "section"], name="cart_items_student_record_id_section_id_unique"
            ),
        ]

    def __str__(self) -> str:
        return f"{self.student_record_id}:{self.section_id}"


class RegistrationAttemptQuerySet(VisibleQuerySet):
    def visible_to(self, user: Any) -> Self:
        """Attempts of records the user can see (RLS ``registration_attempts_record_select``)."""
        return self.filter(student_record_id__in=visible_record_ids(user))


class RegistrationAttempt(models.Model):
    """Every registration attempt with each rule's result, for disputes ("why could I not
    register?"). Append only."""

    student_record = models.ForeignKey(
        "person.StudentRecord", on_delete=models.CASCADE, related_name="registration_attempts"
    )
    term = models.ForeignKey("term.Term", on_delete=models.SET_NULL, null=True, blank=True, related_name="+")
    section = models.ForeignKey(
        "offering.Section", on_delete=models.SET_NULL, null=True, blank=True, related_name="registration_attempts"
    )
    action = models.CharField(_("Action"), max_length=16, choices=AttemptAction.choices)
    outcome = models.CharField(_("Outcome"), max_length=16, choices=AttemptOutcome.choices)
    #: ``[{code, passed, severity, overridden, message}]``
    results = models.JSONField(default=list)
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )
    request_id = models.CharField(pgettext_lazy("registration", "Request ID"), max_length=255, null=True, blank=True)
    attempted_at = models.DateTimeField(pgettext_lazy("registration", "Time"))

    objects = RegistrationAttemptQuerySet.as_manager()

    class Meta:
        db_table = "registration_attempts"
        ordering = ["-attempted_at", "-id"]
        verbose_name = _("registration attempt")
        verbose_name_plural = _("registration attempts")

    def __str__(self) -> str:
        return f"{self.action}:{self.outcome}"

    def __repr__(self) -> str:
        return f"<RegistrationAttempt {self.pk} record={self.student_record_id} {self.action}:{self.outcome}>"

    def failed_results(self) -> list[dict[str, Any]]:
        return [result for result in self.results or [] if not result.get("passed")]

    def failed_summary(self) -> str:
        """Failed rules with their messages, one per line (attempt log list)."""
        lines = []
        for result in self.failed_results():
            code = result.get("code", "")
            label = str(RuleCode(code).label) if code in RuleCode.values else code
            overridden = f" ({_('overridden')})" if result.get("overridden") else ""
            lines.append(f"{label}{overridden}: {result.get('message') or ''}")
        return "\n".join(lines)
