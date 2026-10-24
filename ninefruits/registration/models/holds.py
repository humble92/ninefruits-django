"""Holds and rule overrides (original ``App\\Models\\Registration\\RegistrationHold`` and
``RegistrationOverride``; legacy SRDENY and SRALLOW)."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Self

from django.conf import settings
from django.db import models
from django.db.models import Q
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.utils.translation import pgettext_lazy

from ninefruits.core.models import TimeStampedModel, VisibleQuerySet
from ninefruits.registration.enums import HoldSource, HoldType, RuleCode
from ninefruits.security.enums import Permission

from .enrollment import _scope, visible_record_ids


def _visible(queryset: Any, user: Any) -> Any:
    """Every row for a global ``registration_holds.manage`` grant, else the rows of records the
    user can see. (The policy for a scoped grant looks the record up under the user's own
    student record policies, so it adds nothing beyond the visible records.)"""
    if _scope(user, Permission.REGISTRATION_HOLDS_MANAGE).is_global:
        return queryset
    return queryset.filter(student_record_id__in=visible_record_ids(user))


class RegistrationHoldQuerySet(VisibleQuerySet):
    def in_force(self, at: datetime | None = None) -> Self:
        """Holds in force at the time (not released, started, not ended)."""
        at = at or timezone.now()
        return self.filter(released_at__isnull=True, starts_at__lte=at).filter(
            Q(ends_at__isnull=True) | Q(ends_at__gt=at)
        )

    def visible_to(self, user: Any) -> Self:
        return _visible(self, user)  # type: ignore[no-any-return]


class RegistrationHold(TimeStampedModel):
    """A hold on a student record (legacy SRDENY): blocks registration, and from later phases
    grade viewing or certificates."""

    student_record = models.ForeignKey(
        "person.StudentRecord", on_delete=models.CASCADE, related_name="holds", verbose_name=_("student record")
    )
    hold_type = models.CharField(_("Hold type"), max_length=32, choices=HoldType.choices)
    blocks_registration = models.BooleanField(_("Blocks registration"), default=True)
    blocks_grades = models.BooleanField(_("Blocks grade viewing"), default=False)
    blocks_certificates = models.BooleanField(_("Blocks certificates"), default=False)
    starts_at = models.DateTimeField(_("Starts"))
    ends_at = models.DateTimeField(_("Ends"), null=True, blank=True)
    reason = models.TextField(pgettext_lazy("common", "Reason"))
    source = models.CharField(
        pgettext_lazy("registration", "Source"), max_length=16, choices=HoldSource.choices, default=HoldSource.MANUAL
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )
    released_at = models.DateTimeField(pgettext_lazy("registration", "Released"), null=True, blank=True)
    released_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )
    release_reason = models.TextField(null=True, blank=True)

    objects = RegistrationHoldQuerySet.as_manager()

    class Meta:
        db_table = "registration_holds"
        ordering = ["-starts_at", "-id"]
        verbose_name = _("hold")
        verbose_name_plural = _("holds")

    def __str__(self) -> str:
        return str(HoldType(self.hold_type).label)

    def __repr__(self) -> str:
        return f"<RegistrationHold {self.pk} record={self.student_record_id} {self.hold_type}>"

    def is_in_force(self, at: datetime | None = None) -> bool:
        at = at or timezone.now()
        return self.released_at is None and self.starts_at <= at and (self.ends_at is None or self.ends_at > at)


class RegistrationOverrideQuerySet(VisibleQuerySet):
    def in_force(self, at: datetime | None = None) -> Self:
        at = at or timezone.now()
        return self.filter(revoked_at__isnull=True).filter(Q(expires_at__isnull=True) | Q(expires_at__gt=at))

    def visible_to(self, user: Any) -> Self:
        return _visible(self, user)  # type: ignore[no-any-return]


class RegistrationOverride(TimeStampedModel):
    """A staff-granted exception to one rule for a student in a term, optionally limited to a
    section or course (legacy SRALLOW). Only rules whose rule set allows overrides honour it."""

    student_record = models.ForeignKey(
        "person.StudentRecord",
        on_delete=models.CASCADE,
        related_name="registration_overrides",
        verbose_name=_("student record"),
    )
    term = models.ForeignKey("term.Term", on_delete=models.CASCADE, related_name="+", verbose_name=_("term"))
    rule_code = models.CharField(_("Rule"), max_length=64, choices=RuleCode.choices)
    section = models.ForeignKey(
        "offering.Section",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="+",
        verbose_name=pgettext_lazy("offering", "Section"),
    )
    course = models.ForeignKey(
        "curriculum.Course", on_delete=models.CASCADE, null=True, blank=True, related_name="+", verbose_name=_("course")
    )
    reason = models.TextField(pgettext_lazy("common", "Reason"))
    expires_at = models.DateTimeField(_("Expires"), null=True, blank=True)
    granted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )
    revoked_at = models.DateTimeField(pgettext_lazy("registration", "Revoked"), null=True, blank=True)
    revoked_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )

    objects = RegistrationOverrideQuerySet.as_manager()

    class Meta:
        db_table = "registration_overrides"
        ordering = ["-created_at", "-id"]
        verbose_name = _("rule override")
        verbose_name_plural = _("rule overrides")

    def __str__(self) -> str:
        return str(RuleCode(self.rule_code).label)

    def __repr__(self) -> str:
        return f"<RegistrationOverride {self.pk} record={self.student_record_id} {self.rule_code}>"

    def covers(self, section: Any) -> bool:
        return (self.section_id is None or self.section_id == section.pk) and (
            self.course_id is None or self.course_id == section.course_id
        )
