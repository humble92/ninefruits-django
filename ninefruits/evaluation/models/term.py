"""A term's course evaluation (original ``App\\Models\\Evaluation\\TermEvaluation``): the form, the
minimum responses and response rate for a section's results to show, and when the results were
published. The evaluation period is the course evaluation window of each section's session
(``term_windows``)."""

from __future__ import annotations

from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils.translation import gettext_lazy as _
from django.utils.translation import pgettext_lazy

from ninefruits.core.models import TimeStampedModel, VisibleQuerySet


class TermEvaluation(TimeStampedModel):
    term = models.ForeignKey("term.Term", on_delete=models.RESTRICT, related_name="+", verbose_name=_("term"))
    form = models.ForeignKey(
        "evaluation.EvaluationForm",
        on_delete=models.RESTRICT,
        related_name="term_evaluations",
        db_column="evaluation_form_id",
        verbose_name=_("evaluation form"),
    )
    minimum_responses = models.IntegerField(
        _("Minimum responses"),
        default=5,
        validators=[MinValueValidator(0)],
        help_text=_(
            "A section's results show only with at least this many responses and this response rate, so few "
            "answers cannot point to a student."
        ),
    )
    minimum_response_percent = models.IntegerField(
        _("Minimum response rate (%)"), default=25, validators=[MinValueValidator(0), MaxValueValidator(100)]
    )
    results_published_at = models.DateTimeField(pgettext_lazy("evaluation", "Results published"), null=True, blank=True)
    published_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )

    objects = VisibleQuerySet.as_manager()

    class Meta:
        db_table = "term_evaluations"
        ordering = ["-term__start_date", "-id"]
        verbose_name = _("term evaluation")
        verbose_name_plural = _("term evaluations")
        constraints = [models.UniqueConstraint(fields=["term"], name="term_evaluations_term_id_unique")]

    def __str__(self) -> str:
        return str(self.term)

    @property
    def is_published(self) -> bool:
        return self.results_published_at is not None
