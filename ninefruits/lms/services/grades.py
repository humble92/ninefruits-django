"""The grade entry screen's **Load scores from the LMS** (original ``GradeEntry::importLmsScores``
and ``hasLmsScores``): the final scores of every active platform that pulls scores, loaded into
the score fields as a draft. Nothing is saved until the user saves; submission and finalization
follow the grade workflow (ADR 0011). The grade entry view (``ninefruits.grading``) calls this."""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from django.core.exceptions import PermissionDenied
from django.utils.translation import gettext

from ninefruits.lms.models import LmsPlatform


class LmsScoreImport:
    def available(self, section: Any) -> bool:
        """An active platform pulling final scores has the section linked."""
        from ninefruits.lms.actions import pulls_scores

        return pulls_scores(section)

    def button_label(self) -> str:
        return gettext("Load scores from the LMS")

    def load(self, section: Any, user: Any) -> dict[int, float]:
        """Enrollment id -> score from every active platform that pulls scores (a later platform
        wins for the same student). The user must be allowed to enter the section's grades."""
        from ninefruits.grading.actions import SaveGrades
        from ninefruits.lms.actions import PullGrades

        if not SaveGrades().can_enter(section, user):
            raise PermissionDenied
        scores: dict[int, float] = {}
        pull = PullGrades()
        for platform in LmsPlatform.objects.active().filter(should_pull_grades=True).order_by("pk"):
            scores.update(pull.handle(platform, section, user))
        return scores

    @staticmethod
    def score_text(score: float) -> str:
        """``87.5`` -> ``"87.5"``, ``90.0`` -> ``"90"`` (the score field's text)."""
        text = format(Decimal(str(score)).normalize(), "f")
        return text

    @staticmethod
    def message(count: int) -> str:
        return gettext("%(count)s score(s) loaded from the LMS as a draft. Check them and save.") % {"count": count}
