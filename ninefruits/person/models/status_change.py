"""Status changes of student records (original ``StudentStatusChangeType`` and
``StudentStatusChange``, legacy SRALTERDEF / SRALTER). Kept forever as the record's status
history."""

from __future__ import annotations

from typing import Any, Self

from django.conf import settings
from django.db import models
from django.db.models import Q
from django.utils.translation import gettext_lazy as _
from django.utils.translation import pgettext_lazy

from ninefruits.core.models import TimeStampedModel, VisibleQuerySet
from ninefruits.i18n.fields import TranslatableJSONField
from ninefruits.person.enums import StatusChangeStatus, StudentStatus


class StudentStatusChangeType(TimeStampedModel):
    """Kind of status change, e.g. leave of absence, return, withdrawal, dismissal.
    Institutions may add their own kinds (e.g. military leave) that map to a system status."""

    code = models.CharField(pgettext_lazy("reference", "Code"), max_length=64, unique=True)
    name = TranslatableJSONField(pgettext_lazy("people", "Name"))
    to_status = models.CharField(_("New status"), max_length=32, choices=StudentStatus.choices)
    from_statuses = models.JSONField(_("Allowed from statuses"), default=list)
    can_student_request = models.BooleanField(_("Students can request"), default=False)
    is_system = models.BooleanField(default=False, editable=False)
    is_active = models.BooleanField(pgettext_lazy("reference.fields", "Active"), default=True)
    sort_order = models.IntegerField(_("Order"), default=0)

    objects = VisibleQuerySet.as_manager()

    class Meta:
        db_table = "student_status_change_types"
        ordering = ["sort_order", "code"]
        verbose_name = _("status change type")
        verbose_name_plural = _("status change types")

    def __str__(self) -> str:
        return str(self.name or self.code)

    def applies_from(self, status: StudentStatus | str) -> bool:
        return str(StudentStatus(status)) in [str(value) for value in (self.from_statuses or [])]


class StudentStatusChangeQuerySet(VisibleQuerySet):
    def pending(self) -> Self:
        return self.filter(status=StatusChangeStatus.REQUESTED)

    def visible_to(self, user: Any) -> Self:
        """Changes of records the user may see (``student_status_changes_record_select``)."""
        from .student_record import StudentRecord

        return self.filter(Q(student_record__in=StudentRecord.objects.visible_to(user)))


class StudentStatusChange(TimeStampedModel):
    student_record = models.ForeignKey(
        "person.StudentRecord",
        on_delete=models.CASCADE,
        related_name="status_changes",
        verbose_name=_("Student record"),
    )
    type = models.ForeignKey(
        StudentStatusChangeType,
        on_delete=models.RESTRICT,
        db_column="status_change_type_id",
        related_name="changes",
        verbose_name=_("Change type"),
    )
    from_status = models.CharField(pgettext_lazy("people", "Status"), max_length=32, choices=StudentStatus.choices)
    to_status = models.CharField(_("New status"), max_length=32, choices=StudentStatus.choices)
    effective_date = models.DateField(pgettext_lazy("people", "Effective date"))
    term = models.ForeignKey(
        "term.Term", on_delete=models.SET_NULL, null=True, blank=True, related_name="+", verbose_name=_("Term")
    )
    reason = models.TextField(_("Reason"))
    status = models.CharField(
        _("Request status"), max_length=32, choices=StatusChangeStatus.choices, default=StatusChangeStatus.REQUESTED
    )
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

    objects = StudentStatusChangeQuerySet.as_manager()

    class Meta:
        db_table = "student_status_changes"
        ordering = ["-requested_at", "-id"]
        verbose_name = _("status change")
        verbose_name_plural = _("status changes")

    def __str__(self) -> str:
        return f"{self.student_record} {self.from_status} -> {self.to_status}"

    def __repr__(self) -> str:
        return f"<StudentStatusChange {self.pk} record={self.student_record_id} {self.status}>"

    @property
    def is_pending(self) -> bool:
        return self.status == StatusChangeStatus.REQUESTED
