"""Grade scales (original ``App\\Models\\Grading\\GradeScale`` and ``GradeScaleItem``): letter
grades and grade points (legacy SSCOREDEF), e.g. a 4.5 scale. At most one scale is the default
(partial unique index ``grade_scales_single_default_unique``); it is the institution's scale,
fixed at installation (``SaveGradeScale``)."""

from __future__ import annotations

from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils.translation import gettext_lazy as _
from django.utils.translation import pgettext_lazy

from ninefruits.core.models import TimeStampedModel, VisibleQuerySet
from ninefruits.grading.enums import GradeAppliesTo
from ninefruits.i18n.fields import TranslatableJSONField


class GradeScale(TimeStampedModel):
    code = models.CharField(pgettext_lazy("reference", "Code"), max_length=32, unique=True)
    name = TranslatableJSONField(pgettext_lazy("reference", "Name"))
    max_grade_points = models.DecimalField(
        _("Maximum grade points"),
        max_digits=4,
        decimal_places=2,
        validators=[MinValueValidator(0), MaxValueValidator(99.99)],
    )
    is_default = models.BooleanField(_("Default"), default=False)

    objects = VisibleQuerySet.as_manager()

    class Meta:
        db_table = "grade_scales"
        ordering = ["code"]
        verbose_name = _("grade scale")
        verbose_name_plural = _("grade scales")

    def __str__(self) -> str:
        return str(self.name or self.code)


class GradeScaleItem(TimeStampedModel):
    grade_scale = models.ForeignKey(GradeScale, on_delete=models.CASCADE, related_name="items")
    code = models.CharField(pgettext_lazy("reference", "Grade"), max_length=16)
    name = TranslatableJSONField(pgettext_lazy("reference", "Name"), null=True, blank=True)
    grade_points = models.DecimalField(
        _("Grade points"), max_digits=4, decimal_places=2, null=True, blank=True, validators=[MinValueValidator(0)]
    )
    min_percentage = models.DecimalField(
        _("From (%)"),
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
    )
    max_percentage = models.DecimalField(
        _("To (%)"),
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
    )
    counts_in_gpa = models.BooleanField(_("Counts in GPA"), default=True)
    is_passing = models.BooleanField(_("Passing"), default=True)
    applies_to = models.CharField(
        _("For"),
        max_length=16,
        choices=GradeAppliesTo.choices,
        default=GradeAppliesTo.GRADED,
        help_text=_(
            'Letter grades are for graded courses, P/NP for pass/fail courses; "both" e.g. for I (incomplete).'
        ),
    )
    sort_order = models.IntegerField(_("Order"), default=0)

    objects = VisibleQuerySet.as_manager()

    class Meta:
        db_table = "grade_scale_items"
        ordering = ["sort_order", "id"]
        verbose_name = _("grade")
        verbose_name_plural = _("grades")
        constraints = [
            models.UniqueConstraint(
                fields=["grade_scale", "code"], name="grade_scale_items_grade_scale_id_code_unique"
            ),
        ]

    def __str__(self) -> str:
        return self.code

    @property
    def scale(self) -> GradeScale:
        return self.grade_scale
