from __future__ import annotations

from typing import Any

from django.utils.translation import gettext as _

from ninefruits.offering.models import SectionMeeting
from ninefruits.registration.data import RegistrationContext, RuleCheck
from ninefruits.registration.enums import RuleCode

from .base import RegistrationRule, RuleDefaults


def overlap_minutes(a: SectionMeeting, b: SectionMeeting) -> int:
    """Minutes two weekly meetings overlap (0 on different days, dates or when inactive)."""
    if (
        int(a.weekday) != int(b.weekday)
        or not a.is_active
        or not b.is_active
        or a.end_date < b.start_date
        or b.end_date < a.start_date
    ):
        return 0
    return max(0, min(a.end_minute(), b.end_minute()) - max(a.start_minute(), b.start_minute()))


def conflict_message(section_label: str) -> str:
    return _("The time overlaps with %(section)s.") % {"section": section_label}


class TimeConflictRule(RegistrationRule):
    """Meetings must not overlap the student's other sections (legacy timetable check).
    Parameter ``allowed_overlap_minutes`` tolerates a short overlap (e.g. 10-minute breaks)."""

    code = RuleCode.TIME_CONFLICT

    def defaults(self) -> RuleDefaults:
        return RuleDefaults(parameters={"allowed_overlap_minutes": 0})

    def check(self, context: RegistrationContext, parameters: dict[str, Any]) -> RuleCheck:
        try:
            allowed = max(0, int(parameters.get("allowed_overlap_minutes") or 0))
        except TypeError, ValueError:
            allowed = 0
        meetings = [meeting for meeting in context.section.meetings.all() if meeting.is_active]
        for enrollment in context.term_enrollments():
            for other in enrollment.section.meetings.all():
                if any(overlap_minutes(meeting, other) > allowed for meeting in meetings):
                    return RuleCheck.fail(
                        conflict_message(enrollment.section.label()),
                        {"conflicts_with": enrollment.section_id},
                    )
        return RuleCheck.ok()
