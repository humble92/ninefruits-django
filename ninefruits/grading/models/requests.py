"""Grade change requests and evaluation method requests (original
``App\\Models\\Grading\\GradeChangeRequest`` and ``EvaluationMethodRequest``).

A grade change request is the only way a finalized grade changes (legacy 교무처 edits with
SSCORE_EDIT_BACKUP had no reason or approval): someone other than the requester approves
(``grade_change_requests_second_person_check``), and approval applies it under
``util.guard_finalized_grade``. One open request per grade, one open method request per section
(partial unique indexes)."""

from __future__ import annotations

from typing import Any, Self

from django.conf import settings
from django.db import models
from django.db.models import Q
from django.utils.translation import gettext_lazy as _
from django.utils.translation import pgettext_lazy

from ninefruits.core.models import TimeStampedModel, VisibleQuerySet
from ninefruits.grading.enums import EvaluationMethod, GradeChangeStatus, RequestStatus
from ninefruits.security.enums import Permission


class GradeChangeRequestQuerySet(VisibleQuerySet):
    def pending(self) -> Self:
        return self.filter(status=GradeChangeStatus.PENDING)

    def visible_to(self, user: Any) -> Self:
        """Requests of enrollments the user can see (RLS ``grade_change_requests_select``)."""
        from ninefruits.registration.models import Enrollment

        return self.filter(enrollment_id__in=Enrollment.objects.visible_to(user).values("pk"))

    def in_scope_of(self, user: Any) -> Self:
        """The admin list: the user's own requests and those of sections in their
        ``grade_changes.approve``, ``grade_changes.request`` or ``grades.view`` scope (original
        ``GradeChangeRequestResource::getEloquentQuery``)."""
        from ninefruits.offering.models import Section

        sections = Section.objects.in_scope_of(
            user, Permission.GRADE_CHANGES_APPROVE, Permission.GRADE_CHANGES_REQUEST, Permission.GRADES_VIEW
        ).values("pk")
        return self.filter(Q(requested_by_id=user.pk) | Q(enrollment__section_id__in=sections))


class GradeChangeRequest(TimeStampedModel):
    enrollment = models.ForeignKey(
        "registration.Enrollment", on_delete=models.RESTRICT, related_name="grade_change_requests"
    )
    from_grade_code = models.CharField(max_length=8, null=True, blank=True)
    to_grade_code = models.CharField(pgettext_lazy("grading", "New grade"), max_length=8)
    to_score = models.DecimalField(_("New score"), max_digits=5, decimal_places=2, null=True, blank=True)
    reason = models.TextField(pgettext_lazy("common", "Reason"))
    status = models.CharField(
        pgettext_lazy("registration", "Status"),
        max_length=16,
        choices=GradeChangeStatus.choices,
        default=GradeChangeStatus.PENDING,
    )
    requested_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.RESTRICT, related_name="+")
    requested_at = models.DateTimeField(pgettext_lazy("grading", "Requested"))
    decided_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.RESTRICT, null=True, blank=True, related_name="+"
    )
    decided_at = models.DateTimeField(null=True, blank=True)
    decision_note = models.TextField(pgettext_lazy("grading", "Note"), null=True, blank=True)
    applied_at = models.DateTimeField(null=True, blank=True)

    objects = GradeChangeRequestQuerySet.as_manager()

    class Meta:
        db_table = "grade_change_requests"
        ordering = ["-requested_at", "-id"]
        verbose_name = _("grade change")
        verbose_name_plural = _("grade changes")
        constraints = [
            models.UniqueConstraint(
                fields=["enrollment"], condition=Q(status="pending"), name="grade_change_requests_single_pending_unique"
            ),
        ]

    def __str__(self) -> str:
        return f"{self.from_grade_code or '-'} → {self.to_grade_code}"

    def __repr__(self) -> str:
        return f"<GradeChangeRequest {self.pk} enrollment={self.enrollment_id} {self.status}>"

    @property
    def is_pending(self) -> bool:
        return self.status == GradeChangeStatus.PENDING


class EvaluationMethodRequestQuerySet(VisibleQuerySet):
    def pending(self) -> Self:
        return self.filter(status=RequestStatus.PENDING)

    def visible_to(self, user: Any) -> Self:
        """Requests of sections the user schedules (original
        ``EvaluationMethodRequestResource::getEloquentQuery``) and the user's own. The table has
        no row level security."""
        from ninefruits.offering.models import Section

        if user is None or not getattr(user, "is_authenticated", False):
            return self.none()
        return self.filter(
            Q(section_id__in=Section.objects.manageable_by(user).values("pk")) | Q(requested_by_id=user.pk)
        )


class EvaluationMethodRequest(TimeStampedModel):
    """An instructor's request to evaluate a section relatively (or absolutely again), decided by
    the staff who schedule the section (decided 2026-10-23)."""

    section = models.ForeignKey(
        "offering.Section",
        on_delete=models.RESTRICT,
        related_name="evaluation_method_requests",
        verbose_name=pgettext_lazy("offering", "Section"),
    )
    requested_method = models.CharField(_("Evaluation"), max_length=16, choices=EvaluationMethod.choices)
    reason = models.TextField(pgettext_lazy("common", "Reason"))
    status = models.CharField(
        pgettext_lazy("registration", "Status"),
        max_length=16,
        choices=RequestStatus.choices,
        default=RequestStatus.PENDING,
    )
    requested_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.RESTRICT, related_name="+")
    requested_at = models.DateTimeField(pgettext_lazy("grading", "Requested"))
    decided_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.RESTRICT, null=True, blank=True, related_name="+"
    )
    decided_at = models.DateTimeField(null=True, blank=True)
    decision_note = models.TextField(pgettext_lazy("grading", "Note"), null=True, blank=True)

    objects = EvaluationMethodRequestQuerySet.as_manager()

    class Meta:
        db_table = "evaluation_method_requests"
        ordering = ["-requested_at", "-id"]
        verbose_name = _("evaluation method request")
        verbose_name_plural = _("evaluation method requests")
        constraints = [
            models.UniqueConstraint(
                fields=["section"],
                condition=Q(status="pending"),
                name="evaluation_method_requests_single_pending_unique",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.section_id}: {self.requested_method}"

    def __repr__(self) -> str:
        return f"<EvaluationMethodRequest {self.pk} section={self.section_id} {self.status}>"
