"""The cut line of a session (original ``ChangeSessionPassScore``, decided 2026-10-23): changed
before the results are published, usually after a hard exam; every result already entered is
judged again from its stored scores (total against the new score, the kind's area minimums
unchanged) and the audit record lists who changed. After publication the cut line is fixed and
single results go through corrections.

The results are judged again in the system context after the permission check: the decision is
derived from stored scores and applies to every result of the session, also those of students
outside the manager's own scope (like term records in Phase 6)."""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.utils.translation import gettext as _

from ninefruits.assessment.enums import ScoringMethod
from ninefruits.assessment.models import AssessmentComponentScore, AssessmentResult, AssessmentSession
from ninefruits.audit.logger import audit
from ninefruits.core.db import session_context
from ninefruits.security.enums import Permission

from ._support import json_number, one_decimal, to_decimal


class ChangeSessionPassScore:
    def handle(
        self, session: AssessmentSession, pass_score: Any, staff: Any, reason: str | None = None
    ) -> dict[str, Any]:
        """Returns ``{rejudged, now_passed, now_failed}`` (student numbers)."""
        if not staff.has_perm(Permission.ASSESSMENTS_MANAGE):
            raise PermissionDenied
        session = AssessmentSession.objects.select_related("assessment_type").get(pk=session.pk)
        if session.is_published:
            raise ValidationError(
                {"pass_score": _("The results are published: the pass score cannot change. Use correction requests.")}
            )
        new_score = to_decimal(pass_score)
        if new_score is not None:
            new_score = one_decimal(new_score)
        before = session.pass_score
        summary: dict[str, Any] = {"rejudged": 0, "now_passed": [], "now_failed": []}

        with transaction.atomic():
            session.pass_score = new_score
            session.save(update_fields=["pass_score", "updated_at"])
            effective = session.effective_pass_score()
            kind = session.assessment_type
            if kind.scoring == ScoringMethod.SCORE and effective is not None:
                with session_context().system("assessment:pass_score"):
                    self._rejudge(session, effective, summary)

        reason = (reason or "").strip() or None
        audit(
            "assessment.pass_score_changed",
            session,
            reason=reason,
            properties={"from": json_number(before), "to": json_number(new_score), **summary},
            causer=staff,
        )
        return summary

    def _rejudge(self, session: AssessmentSession, effective: Decimal, summary: dict[str, Any]) -> None:
        minimums = {
            component.pk: component.min_score
            for component in session.assessment_type.components.all()
            if component.min_score is not None
        }
        results = list(
            AssessmentResult.objects.filter(session_id=session.pk).select_related("student_record").order_by("id")
        )
        scores: dict[int, list[AssessmentComponentScore]] = {}
        for score in AssessmentComponentScore.objects.filter(result_id__in=[r.pk for r in results]):
            scores.setdefault(score.result_id, []).append(score)
        for result in results:
            if result.total_score is None:
                continue
            passed = result.total_score >= effective
            for score in scores.get(result.pk, []):
                minimum = minimums.get(score.component_id)
                if minimum is not None and score.score < minimum:
                    passed = False
            summary["rejudged"] += 1
            if passed != result.is_passed:
                result.is_passed = passed
                result.save(update_fields=["is_passed", "updated_at"])
                summary["now_passed" if passed else "now_failed"].append(result.student_record.student_number)
