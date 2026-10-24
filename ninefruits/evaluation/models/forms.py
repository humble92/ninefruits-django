"""Evaluation forms and their questions (original ``App\\Models\\Evaluation\\EvaluationForm`` and
``EvaluationQuestion``; legacy SURCATEGORY + SURCONTENT, loaded by hand-run SQL each term).

A term uses one form. A form whose questions have responses keeps them (results must keep
meaning what was asked); copy the form to change them (``CopyEvaluationForm``)."""

from __future__ import annotations

from typing import Any

from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils.translation import gettext_lazy as _
from django.utils.translation import pgettext_lazy

from ninefruits.core.models import TimeStampedModel, VisibleQuerySet
from ninefruits.evaluation.enums import QuestionType
from ninefruits.i18n.fields import TranslatableJSONField


def responses_exist(**filters: Any) -> bool:
    """Whether any response matches, whoever asks. Responses are hidden from most users by row
    level security; whether a form or a term has responses is not, so the check runs in the
    system context (a manager scoped to one unit must not unlock a form used elsewhere)."""
    from ninefruits.core.db import session_context

    from .responses import EvaluationResponse

    with session_context().system("evaluation:lock-check"):
        return EvaluationResponse.objects.filter(**filters).exists()


class EvaluationForm(TimeStampedModel):
    code = models.CharField(pgettext_lazy("reference", "Code"), max_length=32, unique=True)
    name = TranslatableJSONField(pgettext_lazy("reference", "Name"))
    description = TranslatableJSONField(
        pgettext_lazy("evaluation", "Description"), null=True, blank=True, max_length=2000
    )
    scale_points = models.SmallIntegerField(
        _("Scale points"), default=5, validators=[MinValueValidator(2), MaxValueValidator(10)]
    )
    scale_low_label = TranslatableJSONField(_("Label of 1"), null=True, blank=True)
    scale_high_label = TranslatableJSONField(_("Label of the highest point"), null=True, blank=True)
    is_active = models.BooleanField(pgettext_lazy("reference.fields", "Active"), default=True)

    objects = VisibleQuerySet.as_manager()

    class Meta:
        db_table = "evaluation_forms"
        ordering = ["code"]
        verbose_name = _("evaluation form")
        verbose_name_plural = _("evaluation forms")

    def __str__(self) -> str:
        return f"{self.code} {self.name or ''}".strip()

    def is_locked(self) -> bool:
        """Questions and scale change only while no term's responses use the form."""
        return self.pk is not None and responses_exist(form_id=self.pk)

    def ordered_questions(self) -> list[EvaluationQuestion]:
        return list(self.questions.order_by("sort_order", "id"))


class EvaluationQuestion(TimeStampedModel):
    form = models.ForeignKey(
        EvaluationForm,
        on_delete=models.CASCADE,
        related_name="questions",
        db_column="evaluation_form_id",
        verbose_name=_("evaluation form"),
    )
    sort_order = models.IntegerField(_("Order"), default=0)
    category = TranslatableJSONField(_("Area"), null=True, blank=True)
    text = TranslatableJSONField(_("Question"), max_length=1000)
    question_type = models.CharField(_("Type"), max_length=16, choices=QuestionType.choices, default=QuestionType.SCALE)
    is_required = models.BooleanField(pgettext_lazy("evaluation", "Required"), default=True)
    is_reversed = models.BooleanField(
        _("Reversed"),
        default=False,
        help_text=_("For negatively worded questions: the answer is reversed in averages (5 counts as 1)."),
    )

    objects = VisibleQuerySet.as_manager()

    class Meta:
        db_table = "evaluation_questions"
        ordering = ["sort_order", "id"]
        verbose_name = _("Question")
        verbose_name_plural = _("Questions")

    def __str__(self) -> str:
        return str(self.text or "")

    @property
    def is_scale(self) -> bool:
        return self.question_type == QuestionType.SCALE
