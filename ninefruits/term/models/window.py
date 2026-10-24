"""Term windows (original ``App\\Models\\Term\\TermWindow``): business periods of a term, e.g.
registration for fourth-year students. Several windows of the same type with different
eligibility give staggered openings. Windows about courses belong to a session (the full-term
session unless another is chosen); the database checks the session is of the same term
(composite foreign key) and that only course windows have one (``term_windows_session_check``)."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Self

from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.utils.translation import pgettext_lazy

from ninefruits.core.models import TimeStampedModel, VisibleQuerySet
from ninefruits.core.targeting import TargetCriteria, TargetCriteriaField
from ninefruits.i18n.fields import TranslatableJSONField
from ninefruits.term.enums import TermWindowType

from .term import Term, TermSession


class TermWindowQuerySet(VisibleQuerySet):
    def open_at(self, at: datetime) -> Self:
        return self.filter(opens_at__lte=at, closes_at__gt=at)


class TermWindow(TimeStampedModel):
    term = models.ForeignKey(Term, on_delete=models.CASCADE, related_name="windows")
    session = models.ForeignKey(
        TermSession,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="windows",
        db_column="term_session_id",
        # The real constraint is the composite (term_session_id, term_id) foreign key.
        db_constraint=False,
        verbose_name=pgettext_lazy("reference", "Session"),
        help_text=_(
            "Course deadlines follow the session of the course: the full term unless the window is "
            "for a shorter session."
        ),
    )
    window_type = models.CharField(_("Window"), max_length=64, choices=TermWindowType.choices)
    name = TranslatableJSONField(_("Name (optional)"), null=True, blank=True)
    opens_at = models.DateTimeField(pgettext_lazy("reference", "Opens"))
    closes_at = models.DateTimeField(pgettext_lazy("reference", "Closes"))
    eligibility = TargetCriteriaField(_("Eligibility"), null=True, blank=True)

    objects = TermWindowQuerySet.as_manager()

    class Meta:
        db_table = "term_windows"
        ordering = ["opens_at", "id"]
        verbose_name = _("term window")
        verbose_name_plural = _("term windows")

    def __str__(self) -> str:
        return f"{self.type.label} {self.name or ''}".strip()

    @property
    def type(self) -> TermWindowType:
        return TermWindowType(self.window_type)

    def save(self, *args: Any, **kwargs: Any) -> None:
        if not self.type.is_course_scoped():
            self.session_id = None
        elif self.session_id is None:
            self.session_id = (
                TermSession.objects.filter(term_id=self.term_id, is_full_term=True).values_list("id", flat=True).first()
            )
        # timestamp(0) columns hold whole seconds.
        for name in ("opens_at", "closes_at"):
            value = getattr(self, name)
            if isinstance(value, datetime) and value.microsecond:
                setattr(self, name, value.replace(microsecond=0))
        super().save(*args, **kwargs)

    def is_open_at(self, at: datetime | None = None) -> bool:
        at = at or timezone.now()
        return self.opens_at <= at < self.closes_at

    @property
    def criteria(self) -> TargetCriteria:
        return TargetCriteria.coerce(self.eligibility)
