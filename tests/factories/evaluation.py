"""Factories for course evaluation (the original tests created the rows with
``EvaluationForm::query()->create(...)``)."""

from __future__ import annotations

import factory

from ninefruits.evaluation.enums import QuestionType
from ninefruits.evaluation.models import EvaluationForm, EvaluationQuestion, TermEvaluation
from tests.factories.term import TermFactory


class EvaluationFormFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = EvaluationForm

    code = factory.Sequence(lambda n: f"F{n}")
    name = factory.LazyAttribute(lambda o: {"en": f"Form {o.code}"})
    scale_points = 5


class EvaluationQuestionFactory(factory.django.DjangoModelFactory):
    """``EvaluationQuestionFactory(form=form, text={"en": "Clear"}, is_reversed=True)``."""

    class Meta:
        model = EvaluationQuestion

    form = factory.SubFactory(EvaluationFormFactory)
    sort_order = factory.Sequence(lambda n: n + 1)
    text = factory.Sequence(lambda n: {"en": f"Question {n}"})
    question_type = QuestionType.SCALE


class TermEvaluationFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = TermEvaluation

    term = factory.SubFactory(TermFactory, published=True)
    form = factory.SubFactory(EvaluationFormFactory)
