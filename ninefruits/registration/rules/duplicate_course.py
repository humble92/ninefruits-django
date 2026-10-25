from __future__ import annotations

from typing import Any

from django.utils.translation import gettext as _

from ninefruits.registration.data import RegistrationContext, RuleCheck
from ninefruits.registration.enums import RuleCode

from .base import RegistrationRule, RuleDefaults


def duplicate_message(section_label: str) -> str:
    return _("You are already registered in %(section)s.") % {"section": section_label}


class DuplicateCourseRule(RegistrationRule):
    """One section of a course per term (also a partial unique index on enrollments)."""

    code = RuleCode.DUPLICATE_COURSE

    def defaults(self) -> RuleDefaults:
        return RuleDefaults(allows_override=False)

    def check(self, context: RegistrationContext, parameters: dict[str, Any]) -> RuleCheck:
        other = next(
            (e for e in context.term_enrollments() if e.course_id == context.section.course_id),
            None,
        )
        return RuleCheck.ok() if other is None else RuleCheck.fail(duplicate_message(other.section.label()))
