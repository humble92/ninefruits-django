from __future__ import annotations

from typing import Any

from django.utils.translation import gettext as _

from ninefruits.offering.enums import SectionStatus
from ninefruits.registration.data import RegistrationContext, RuleCheck
from ninefruits.registration.enums import AttemptAction, RuleCode

from .base import RegistrationRule, RuleDefaults


class SectionOpenRule(RegistrationRule):
    """The section is published (always on)."""

    code = RuleCode.SECTION_OPEN

    def defaults(self) -> RuleDefaults:
        return RuleDefaults(allows_override=False)

    def applies_to(self, action: AttemptAction) -> bool:
        return action not in (AttemptAction.DROP, AttemptAction.WITHDRAW)

    def check(self, context: RegistrationContext, parameters: dict[str, Any]) -> RuleCheck:
        if context.section.status == SectionStatus.PUBLISHED:
            return RuleCheck.ok()
        return RuleCheck.fail(_("This section is not open for registration."))
