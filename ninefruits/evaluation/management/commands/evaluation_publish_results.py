"""Publishes a term's course evaluation results to the instructors (original
``evaluation:publish-results``): sections with enough responses show their results from now on."""

from __future__ import annotations

from typing import Any

from django.core.management.base import CommandParser

from ninefruits.core.commands import AuditedCommand
from ninefruits.evaluation.actions import ManageTermEvaluation
from ninefruits.evaluation.models import EvaluationResponse, TermEvaluation
from ninefruits.term.models import Term


class Command(AuditedCommand):
    help = "Publish a term's course evaluation results to the instructors (sections with enough responses)"

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument("term", help="Term code")

    def handle(self, *args: Any, **options: Any) -> int:  # type: ignore[override]  # exit code (StatusCommand)
        term = Term.objects.filter(code=options["term"]).first()
        evaluation = TermEvaluation.objects.filter(term_id=term.pk).first() if term is not None else None
        if evaluation is None:
            self.error("Unknown term code, or the term has no course evaluation.")
            return self.FAILURE

        already = evaluation.results_published_at is not None
        ManageTermEvaluation().publish(evaluation, self.actor())
        responses = EvaluationResponse.objects.filter(term_id=evaluation.term_id).count()

        self.record_result({"responses": responses, "already_published": already})
        self.info("Already published." if already else f"Published ({responses} response(s)).")
        return self.SUCCESS
