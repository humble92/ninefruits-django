"""Copies a form with its questions (original ``CopyEvaluationForm``), e.g. to change a form whose
questions are locked by responses."""

from __future__ import annotations

from typing import Any

from django.core.exceptions import PermissionDenied
from django.db import transaction

from ninefruits.audit.logger import audit
from ninefruits.evaluation.models import EvaluationForm, EvaluationQuestion
from ninefruits.security.enums import Permission


class CopyEvaluationForm:
    def __call__(self, form: EvaluationForm, code: str, staff: Any) -> EvaluationForm:
        if not staff.has_perm(Permission.EVALUATIONS_MANAGE):
            raise PermissionDenied
        with transaction.atomic():
            copy = EvaluationForm(
                code=code,
                name=form.name_translations,
                description=form.description_translations,
                scale_points=form.scale_points,
                scale_low_label=form.scale_low_label_translations,
                scale_high_label=form.scale_high_label_translations,
                is_active=form.is_active,
            )
            copy.save()
            EvaluationQuestion.objects.bulk_create(
                [
                    EvaluationQuestion(
                        form=copy,
                        sort_order=question.sort_order,
                        category=question.category_translations,
                        text=question.text_translations,
                        question_type=question.question_type,
                        is_required=question.is_required,
                        is_reversed=question.is_reversed,
                    )
                    for question in form.ordered_questions()
                ]
            )
            audit("evaluation_form.copied", copy, properties={"from": form.code}, causer=staff)
        return copy
