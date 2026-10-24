from __future__ import annotations

from collections import OrderedDict
from typing import Any

from django.utils import timezone
from django.utils.translation import gettext as _

from ninefruits.curriculum.enums import RequisiteKind
from ninefruits.registration.data import RegistrationContext, RuleCheck
from ninefruits.registration.enums import RuleCode
from ninefruits.registration.services.course_history import CourseHistory

from .base import RegistrationRule


def missing_message(missing: list[str]) -> str:
    return _("Prerequisites not met: %(courses)s.") % {"courses": ", ".join(missing)}


class RequisitesRule(RegistrationRule):
    """Prerequisites and corequisites of the course version (legacy SPCOURSE): in each group one
    course (or an equivalent valid now) must be passed, at the minimum grade if set; a
    prerequisite marked ``allows_concurrent``, and a corequisite, may also be taken this term.
    Courses taken on the person's earlier student records count."""

    code = RuleCode.REQUISITES

    def __init__(self, history: CourseHistory | None = None) -> None:
        self.history = history or CourseHistory()

    def check(self, context: RegistrationContext, parameters: dict[str, Any]) -> RuleCheck:
        requisites = list(context.section.version.requisites.select_related("required_course").order_by("id"))
        this_term = {e.course_id for e in context.term_enrollments()}
        groups: OrderedDict[str, list[Any]] = OrderedDict()
        for requisite in requisites:
            groups.setdefault(f"{requisite.kind}-{requisite.group_number}", []).append(requisite)
        on = timezone.localdate(context.at)
        missing = []
        for group in groups.values():
            met = False
            for requisite in group:
                accepted = self.history.accepted_course_ids(requisite.required_course_id, on)
                concurrent = requisite.kind == RequisiteKind.COREQUISITE or requisite.allows_concurrent
                if self.history.has_passed(context.record, accepted, requisite.minimum_grade) or (
                    concurrent and this_term.intersection(accepted)
                ):
                    met = True
                    break
            if not met:
                missing.append(" / ".join(requisite.required_course.code for requisite in group))
        if not missing:
            return RuleCheck.ok()
        return RuleCheck.fail(missing_message(missing), {"missing": missing})
