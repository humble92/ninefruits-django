"""The registration rules in evaluation order (original ``RuleCatalog``). Rule sets configure
them; they are not stored as a catalog table (like permissions, the code is the catalog)."""

from __future__ import annotations

from ninefruits.registration import rules
from ninefruits.registration.enums import RuleCode

RULES: dict[RuleCode, type[rules.RegistrationRule]] = {
    RuleCode.WINDOW: rules.WindowRule,
    RuleCode.SECTION_OPEN: rules.SectionOpenRule,
    RuleCode.HOLD: rules.HoldRule,
    RuleCode.STUDENT_STATUS: rules.StudentStatusRule,
    RuleCode.ELIGIBILITY: rules.EligibilityRule,
    RuleCode.DUPLICATE_COURSE: rules.DuplicateCourseRule,
    RuleCode.TIME_CONFLICT: rules.TimeConflictRule,
    RuleCode.CREDIT_LIMIT: rules.CreditLimitRule,
    RuleCode.REQUISITES: rules.RequisitesRule,
    RuleCode.REPEAT_COURSE: rules.RepeatCourseRule,
}


class RuleCatalog:
    def all(self) -> list[rules.RegistrationRule]:
        return [rule() for rule in RULES.values()]

    def get(self, code: RuleCode | str) -> rules.RegistrationRule:
        return RULES[RuleCode(code)]()

    def configurable(self) -> list[rules.RegistrationRule]:
        """Rules a rule set has rows for (not the core rules)."""
        return [rule for rule in self.all() if not rule.code.is_core()]
