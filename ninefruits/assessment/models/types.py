"""Examination kinds and their scored areas (original ``App\\Models\\Assessment\\AssessmentType``
and ``AssessmentComponent``; legacy CET_TYPE, the SSCORE_ADD exam numbers and COMEXAMTYPE).

A kind defines how it is scored (``score``: the areas or one total against the pass score, each
area at or above its minimum; ``pass_fail``: staff decide) and what passes. Configuration data:
no row level security."""

from __future__ import annotations

from decimal import Decimal

from django.db import models
from django.utils.translation import gettext_lazy as _
from django.utils.translation import pgettext_lazy

from ninefruits.assessment.enums import AssessmentCategory, ScoringMethod
from ninefruits.core.models import TimeStampedModel, VisibleQuerySet
from ninefruits.i18n.fields import TranslatableJSONField


class AssessmentType(TimeStampedModel):
    code = models.CharField(pgettext_lazy("reference", "Code"), max_length=32, unique=True)
    name = TranslatableJSONField(pgettext_lazy("reference", "Name"))
    category = models.CharField(
        _("Category"), max_length=16, choices=AssessmentCategory.choices, default=AssessmentCategory.COMPREHENSIVE
    )
    scoring = models.CharField(
        _("Scoring"),
        max_length=16,
        choices=ScoringMethod.choices,
        default=ScoringMethod.SCORE,
        help_text=_(
            "Score: the areas (or one total) against the pass score, with each area at or above its minimum. "
            "Pass/fail: staff decide for each student."
        ),
    )
    max_score = models.DecimalField(
        _("Maximum score"),
        max_digits=6,
        decimal_places=1,
        null=True,
        blank=True,
        help_text=_("For kinds without areas. With areas, the maximum is their sum."),
    )
    pass_score = models.DecimalField(
        _("Pass score"),
        max_digits=6,
        decimal_places=1,
        null=True,
        blank=True,
        help_text=_("Total needed to pass. A session can override it."),
    )
    allows_external = models.BooleanField(
        _("External results"),
        default=False,
        help_text=_("Results from an outside body (TOPIK, HSK, ...) can be recorded with an evidence file."),
    )
    is_active = models.BooleanField(pgettext_lazy("reference.fields", "Active"), default=True)
    sort_order = models.IntegerField(_("Order"), default=0)

    objects = VisibleQuerySet.as_manager()

    class Meta:
        db_table = "assessment_types"
        ordering = ["sort_order", "code"]
        verbose_name = _("Examination kind")
        verbose_name_plural = _("Examination kinds")

    def __str__(self) -> str:
        return str(self.name or self.code)

    def __repr__(self) -> str:
        return f"<AssessmentType {self.pk} {self.code}>"

    @property
    def is_scored(self) -> bool:
        return self.scoring == ScoringMethod.SCORE

    def ordered_components(self) -> list[AssessmentComponent]:
        """The areas in their order (original ``components`` relation, ordered by sort_order)."""
        return list(self.components.order_by("sort_order", "id"))


class AssessmentComponent(TimeStampedModel):
    """A scored area of a kind (listening, reading, ...), with its maximum and an optional
    minimum to pass."""

    assessment_type = models.ForeignKey(
        AssessmentType,
        on_delete=models.CASCADE,
        related_name="components",
        verbose_name=pgettext_lazy("assessment", "Kind"),
    )
    code = models.CharField(
        pgettext_lazy("reference", "Code"),
        max_length=32,
        help_text=_("Column name in the results CSV, e.g. LISTENING."),
    )
    name = TranslatableJSONField(pgettext_lazy("reference", "Name"))
    max_score = models.DecimalField(_("Maximum score"), max_digits=6, decimal_places=1)
    min_score = models.DecimalField(
        _("Minimum to pass"),
        max_digits=6,
        decimal_places=1,
        null=True,
        blank=True,
        help_text=_("Below this the student fails whatever the total."),
    )
    sort_order = models.IntegerField(_("Order"), default=0)

    objects = VisibleQuerySet.as_manager()

    class Meta:
        db_table = "assessment_components"
        ordering = ["sort_order", "id"]
        verbose_name = _("Areas")
        verbose_name_plural = _("Areas")
        constraints = [
            models.UniqueConstraint(
                fields=["assessment_type", "code"], name="assessment_components_assessment_type_id_code_unique"
            ),
        ]

    def __str__(self) -> str:
        return str(self.name or self.code)

    def __repr__(self) -> str:
        return f"<AssessmentComponent {self.pk} {self.code}>"

    def label(self) -> str:
        """``Listening (/25)`` (original result form label)."""
        return f"{self.name} (/{format_score(self.max_score)})"


def format_score(value: Decimal | None) -> str | None:
    """Scores are ``numeric(6,1)``: shown with one decimal like the original ``decimal:1`` cast."""
    if value is None:
        return None
    return format(Decimal(value).quantize(Decimal("0.1")), "f")
