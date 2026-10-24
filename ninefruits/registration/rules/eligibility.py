from __future__ import annotations

from typing import Any

from django.utils.translation import gettext as _

from ninefruits.registration.data import RegistrationContext, RuleCheck
from ninefruits.registration.enums import RuleCode

from .base import RegistrationRule


class EligibilityRule(RegistrationRule):
    """The section's include and exclude conditions (legacy TARGET_ST, TARGET_ST_DEPART,
    TARGET_ST_GRADE: department, admission year, both)."""

    code = RuleCode.ELIGIBILITY

    def check(self, context: RegistrationContext, parameters: dict[str, Any]) -> RuleCheck:
        if context.section.admits(context.record):
            return RuleCheck.ok()
        return RuleCheck.fail(_("This section is not open to you."))
