"""A student's application for a second major or minor (original
``AdditionalProgramRequest``), decided by staff of the target program. Approval adds a
``student_record_programs`` row starting with the term."""

from __future__ import annotations

from typing import Any, Self

from django.conf import settings
from django.db import models
from django.db.models import Q
from django.utils.translation import gettext_lazy as _
from django.utils.translation import pgettext_lazy

from ninefruits.core.models import TimeStampedModel, VisibleQuerySet
from ninefruits.person.enums import AdditionalProgramRequestStatus, AdditionalProgramRole
from ninefruits.security.enums import Permission


def _approve_scope(user: Any) -> Any:
    from ninefruits.security.services.authorization import authorization

    return authorization().scope_for(user, Permission.ADDITIONAL_PROGRAMS_APPROVE)


class AdditionalProgramRequestQuerySet(VisibleQuerySet):
    def pending(self) -> Self:
        return self.filter(status=AdditionalProgramRequestStatus.REQUESTED)

    def decidable_by(self, user: Any) -> Self:
        """Requests the user may decide (``additional_programs.approve`` covering the target
        program)."""
        scope = _approve_scope(user)
        if scope.is_global:
            return self
        condition = Q(pk__in=[])
        if scope.org_unit_ids:
            condition |= Q(org_unit_id__in=scope.org_unit_ids)
        if scope.program_ids:
            condition |= Q(program_id__in=scope.program_ids)
        return self.filter(condition)

    def visible_to(self, user: Any) -> Self:
        """Requests of records the user may see, and requests the user may decide (RLS
        ``additional_program_requests_record_select`` and ``..._approver_select``)."""
        from .student_record import StudentRecord

        return self.filter(
            Q(student_record__in=StudentRecord.objects.visible_to(user))
            | Q(pk__in=self.decidable_by(user).values("pk"))
        )


class AdditionalProgramRequest(TimeStampedModel):
    student_record = models.ForeignKey(
        "person.StudentRecord",
        on_delete=models.CASCADE,
        related_name="additional_program_requests",
        verbose_name=_("Student record"),
    )
    program = models.ForeignKey(
        "organization.Program", on_delete=models.RESTRICT, related_name="+", verbose_name=_("Applied program")
    )
    org_unit = models.ForeignKey("organization.OrgUnit", on_delete=models.RESTRICT, related_name="+")
    role = models.CharField(pgettext_lazy("people", "Kind"), max_length=16, choices=AdditionalProgramRole.choices)
    term = models.ForeignKey("term.Term", on_delete=models.RESTRICT, related_name="+", verbose_name=_("Starting term"))
    status = models.CharField(
        _("Request status"),
        max_length=16,
        choices=AdditionalProgramRequestStatus.choices,
        default=AdditionalProgramRequestStatus.REQUESTED,
    )
    statement = models.TextField(_("Statement"), null=True, blank=True)
    requested_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
        verbose_name=pgettext_lazy("people", "Requested by"),
    )
    requested_at = models.DateTimeField(_("Requested at"))
    decided_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
        verbose_name=pgettext_lazy("people", "Decided by"),
    )
    decided_at = models.DateTimeField(null=True, blank=True)
    decision_note = models.TextField(pgettext_lazy("people", "Decision note"), null=True, blank=True)
    student_record_program = models.ForeignKey(
        "person.StudentRecordProgram", on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )

    objects = AdditionalProgramRequestQuerySet.as_manager()

    class Meta:
        db_table = "additional_program_requests"
        ordering = ["-requested_at", "-id"]
        verbose_name = _("second major or minor application")
        verbose_name_plural = _("second major and minor applications")

    def __str__(self) -> str:
        return f"{self.student_record} {self.program}"

    def __repr__(self) -> str:
        return f"<AdditionalProgramRequest {self.pk} record={self.student_record_id} {self.status}>"

    def is_decidable_by(self, user: Any) -> bool:
        return bool(_approve_scope(user).covers(self.org_unit_id, self.program_id))

    @property
    def is_pending(self) -> bool:
        return self.status == AdditionalProgramRequestStatus.REQUESTED
