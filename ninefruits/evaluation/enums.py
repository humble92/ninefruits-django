"""Course evaluation enums (original ``App\\Domain\\Evaluation\\Enums``)."""

from __future__ import annotations

from django.db import models
from django.utils.translation import pgettext_lazy


class QuestionType(models.TextChoices):
    """A question answered on the form's scale or with a comment."""

    SCALE = "scale", pgettext_lazy("evaluation.question_types", "Scale")
    TEXT = "text", pgettext_lazy("evaluation.question_types", "Comment")
