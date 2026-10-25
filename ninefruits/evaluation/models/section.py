"""Response rates per section for staff (original Filament ``SectionEvaluationResource`` on the
section model, legacy counsel/academy_list.php): a proxy of ``offering.Section`` so the course
evaluation screens have their own list next to the section screens."""

from __future__ import annotations

from typing import Any, Self

from django.utils.translation import gettext_lazy as _

from ninefruits.offering.models import Section
from ninefruits.offering.models.section import SectionQuerySet
from ninefruits.security.enums import Permission


class SectionEvaluationQuerySet(SectionQuerySet):
    def visible_to(self, user: Any) -> Self:
        """Sections of terms with a course evaluation, offered by units in the user's
        ``evaluations.view`` or ``evaluations.manage`` scope."""
        from .term import TermEvaluation

        return self.in_scope_of(user, Permission.EVALUATIONS_VIEW, Permission.EVALUATIONS_MANAGE).filter(
            term_id__in=TermEvaluation.objects.values("term_id")
        )


class SectionEvaluation(Section):
    objects = SectionEvaluationQuerySet.as_manager()  # type: ignore[misc]  # a proxy may narrow the manager

    class Meta:
        proxy = True
        verbose_name = _("section response")
        verbose_name_plural = _("responses by section")
