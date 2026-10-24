"""The ten registration rules (porting-plan 10.6). Evaluation order and defaults are in
``ninefruits.registration.services.rule_catalog``."""

from .base import ADDING, RegistrationRule, RuleDefaults
from .credit_limit import CreditLimitRule
from .duplicate_course import DuplicateCourseRule
from .eligibility import EligibilityRule
from .hold import HoldRule
from .repeat_course import RepeatCourseRule
from .requisites import RequisitesRule
from .section_open import SectionOpenRule
from .student_status import StudentStatusRule
from .time_conflict import TimeConflictRule, overlap_minutes
from .window import WindowRule

__all__ = [
    "ADDING",
    "CreditLimitRule",
    "DuplicateCourseRule",
    "EligibilityRule",
    "HoldRule",
    "RegistrationRule",
    "RepeatCourseRule",
    "RequisitesRule",
    "RuleDefaults",
    "SectionOpenRule",
    "StudentStatusRule",
    "TimeConflictRule",
    "WindowRule",
    "overlap_minutes",
]
