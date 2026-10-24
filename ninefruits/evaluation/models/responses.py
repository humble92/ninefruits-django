"""Completions and anonymous responses (ADR 0012, original ``EvaluationCompletion``,
``EvaluationResponse`` and ``EvaluationAnswer``).

The completion records *that* an enrollment was evaluated, and when. The response records *what*
was answered for the section, with no student, no sequence and no time: its id is a random UUID
(v4), so neither the id nor a timestamp can be matched against the completion order. Answers have
the composite key (response, question). None of the three tables has a data audit trigger (the
audit would record the acting student); they are written by ``SubmitEvaluation`` in the system
context after it checked the student. Students never read responses (row level security);
instructors read their sections' responses once the term's results are published."""

from __future__ import annotations

import uuid
from typing import Any, Self

from django.db import models

from ninefruits.core.models import VisibleQuerySet
from ninefruits.security.enums import Permission


class EvaluationCompletion(models.Model):
    """That an enrollment was evaluated, and when. Says nothing about the answers."""

    enrollment = models.ForeignKey(
        "registration.Enrollment", on_delete=models.RESTRICT, related_name="evaluation_completions"
    )
    completed_at = models.DateTimeField()

    objects = VisibleQuerySet.as_manager()

    class Meta:
        db_table = "evaluation_completions"
        constraints = [
            models.UniqueConstraint(fields=["enrollment"], name="evaluation_completions_enrollment_id_unique")
        ]

    def __str__(self) -> str:
        return f"{self.enrollment_id}"

    def __repr__(self) -> str:
        return f"<EvaluationCompletion {self.pk} enrollment={self.enrollment_id}>"


class EvaluationResponseQuerySet(VisibleQuerySet):
    def visible_to(self, user: Any) -> Self:
        """Responses the user may read (RLS ``evaluation_responses_staff_select`` and
        ``_instructor_select``): staff with ``evaluations.view`` or ``evaluations.manage`` for
        the offering unit; a section's instructors once the term's results are published."""
        from ninefruits.offering.models import Section

        from .term import TermEvaluation

        if user is None or not getattr(user, "is_authenticated", False):
            return self.none()
        staff = Section.objects.in_scope_of(user, Permission.EVALUATIONS_VIEW, Permission.EVALUATIONS_MANAGE)
        condition = models.Q(section_id__in=staff.values("pk"))
        person_id = getattr(user, "person_id", None)
        if person_id is not None:
            published = TermEvaluation.objects.filter(results_published_at__isnull=False).values("term_id")
            condition |= models.Q(
                term_id__in=published, section_id__in=Section.objects.taught_by(person_id).values("pk")
            )
        return self.filter(condition)


class EvaluationResponse(models.Model):
    """One anonymous response for a section. No ``created_at``, no ordering: neither may follow
    the completion order."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    term = models.ForeignKey("term.Term", on_delete=models.RESTRICT, related_name="+")
    section = models.ForeignKey("offering.Section", on_delete=models.RESTRICT, related_name="evaluation_responses")
    form = models.ForeignKey(
        "evaluation.EvaluationForm", on_delete=models.RESTRICT, related_name="responses", db_column="evaluation_form_id"
    )

    objects = EvaluationResponseQuerySet.as_manager()

    class Meta:
        db_table = "evaluation_responses"

    def __str__(self) -> str:
        return str(self.pk)

    def __repr__(self) -> str:
        return f"<EvaluationResponse section={self.section_id}>"


class EvaluationAnswer(models.Model):
    """The answer to one question: a scale value or a comment."""

    pk = models.CompositePrimaryKey("response_id", "question_id")
    response = models.ForeignKey(
        EvaluationResponse, on_delete=models.CASCADE, related_name="answers", db_column="evaluation_response_id"
    )
    question = models.ForeignKey(
        "evaluation.EvaluationQuestion",
        on_delete=models.RESTRICT,
        related_name="answers",
        db_column="evaluation_question_id",
    )
    value = models.SmallIntegerField(null=True, blank=True)
    comment = models.TextField(null=True, blank=True)

    objects = VisibleQuerySet.as_manager()

    class Meta:
        db_table = "evaluation_answers"

    def __str__(self) -> str:
        return f"{self.question_id}"

    def __repr__(self) -> str:
        return f"<EvaluationAnswer question={self.question_id}>"
