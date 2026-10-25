from __future__ import annotations

from typing import Any

from django.utils import timezone
from django.utils.translation import gettext as _

from ninefruits.registration.data import RegistrationContext, RuleCheck
from ninefruits.registration.enums import RuleCode
from ninefruits.registration.services.course_history import CourseHistory

from .base import RegistrationRule, RuleDefaults


def retake_message() -> str:
    return _("This registration is a retake.")


class RepeatCourseRule(RegistrationRule):
    """Taking a course again (it or an equivalent was completed before on this record) is a
    retake (legacy SSC_RAPPLY marking, now automatic). Parameters: ``allowed`` (false: no
    retakes), ``max_attempts`` (total including this one), ``below_grade`` (only when the best
    earlier grade is below this code). Courses that may be repeated for credit are not retakes.
    Passes with a note when it is a retake; the enrollment is marked."""

    code = RuleCode.REPEAT_COURSE

    def __init__(self, history: CourseHistory | None = None) -> None:
        self.history = history or CourseHistory()

    def defaults(self) -> RuleDefaults:
        return RuleDefaults(parameters={"allowed": True, "max_attempts": None, "below_grade": None})

    def check(self, context: RegistrationContext, parameters: dict[str, Any]) -> RuleCheck:
        section = context.section
        if section.version.is_repeatable:
            return RuleCheck.ok()
        accepted = self.history.accepted_course_ids(section.course_id, timezone.localdate(context.at))
        earlier = self.history.earlier_attempts(context.record, accepted, section.term_id)
        if not earlier:
            return RuleCheck.ok()
        details = {"repeats_enrollment_id": earlier[0].pk}
        if not parameters.get("allowed", True):
            return RuleCheck.fail(_("You have already taken this course and retakes are not allowed."), details)
        maximum = parameters.get("max_attempts")
        if maximum is not None and len(earlier) + 1 > int(maximum):
            return RuleCheck.fail(
                _("You have reached the maximum of %(max)s attempts for this course.") % {"max": maximum}, details
            )
        below = parameters.get("below_grade")
        if below is not None and any(
            enrollment.is_passed and self.history.meets_minimum(enrollment.grade_code, str(below))
            for enrollment in earlier
        ):
            return RuleCheck.fail(_("Retakes are allowed only for grades below %(grade)s.") % {"grade": below}, details)
        return RuleCheck.ok(retake_message(), details)
