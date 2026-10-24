"""Sets up a term's course evaluation (form and minimums) and publishes its results to the
instructors (original ``ManageTermEvaluation``). The evaluation period is the course evaluation
window of the sessions."""

from __future__ import annotations

from typing import Any

from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.utils import timezone
from django.utils.translation import gettext as _

from ninefruits.audit.logger import audit
from ninefruits.evaluation.models import EvaluationForm, TermEvaluation
from ninefruits.evaluation.models.forms import responses_exist
from ninefruits.evaluation.settings import EvaluationSettings
from ninefruits.security.enums import Permission


class ManageTermEvaluation:
    def __init__(self, settings: EvaluationSettings | None = None) -> None:
        self._settings = settings

    @property
    def settings(self) -> EvaluationSettings:
        if self._settings is None:
            self._settings = EvaluationSettings.load()
        return self._settings

    def prepare(
        self,
        term: Any,
        form: EvaluationForm,
        staff: Any | None,
        minimum_responses: int | None = None,
        minimum_percent: int | None = None,
    ) -> TermEvaluation:
        """Creates or changes the term's evaluation. The form cannot change once the term has
        responses. Minimums left empty keep the current values (a new evaluation takes the
        settings' defaults)."""
        self._authorize(staff)
        evaluation = TermEvaluation.objects.filter(term_id=term.pk).first()
        exists = evaluation is not None
        if evaluation is None:
            evaluation = TermEvaluation(term_id=term.pk)
        if exists and evaluation.form_id != form.pk and responses_exist(term_id=term.pk):
            raise ValidationError({"evaluation_form_id": _("The term already has responses with its form.")})
        evaluation.form = form
        evaluation.minimum_responses = (
            minimum_responses
            if minimum_responses is not None
            else (evaluation.minimum_responses if exists else self.settings.minimum_responses)
        )
        evaluation.minimum_response_percent = (
            minimum_percent
            if minimum_percent is not None
            else (evaluation.minimum_response_percent if exists else self.settings.minimum_response_percent)
        )
        with transaction.atomic():
            evaluation.save()
            audit(
                "evaluation.prepared",
                evaluation,
                properties={"term": term.code, "form": form.code},
                causer=staff,
            )
        return evaluation

    def publish(self, evaluation: TermEvaluation, staff: Any | None) -> TermEvaluation:
        """Instructors see their sections' results from now on (sections with enough
        responses). Publishing twice changes nothing."""
        self._authorize(staff)
        if evaluation.results_published_at is not None:
            return evaluation
        evaluation.results_published_at = timezone.now().replace(microsecond=0)
        evaluation.published_by_id = staff.pk if staff is not None else None
        with transaction.atomic():
            evaluation.save(update_fields=["results_published_at", "published_by", "updated_at"])
            audit("evaluation.published", evaluation, properties={"term_id": evaluation.term_id}, causer=staff)
        return evaluation

    @staticmethod
    def _authorize(staff: Any | None) -> None:
        if staff is not None and not staff.has_perm(Permission.EVALUATIONS_MANAGE):
            raise PermissionDenied
