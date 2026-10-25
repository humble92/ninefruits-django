"""A registration rule (porting-plan 10.6, original ``RegistrationRule`` interface). Rules only
answer; the engine applies the term's configuration."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, ClassVar

from ninefruits.registration.data import RegistrationContext, RuleCheck
from ninefruits.registration.enums import AttemptAction, RuleCode, RuleSeverity

#: The actions that add a registration (the cart pre-check included).
ADDING: frozenset[AttemptAction] = frozenset(
    {AttemptAction.ENROLL, AttemptAction.WAITLIST, AttemptAction.PROMOTE, AttemptAction.CART}
)


@dataclass(frozen=True)
class RuleDefaults:
    """Configuration when the term has no rule set (and the starting point of a new one)."""

    severity: RuleSeverity = RuleSeverity.BLOCK
    allows_override: bool = True
    parameters: dict[str, Any] = field(default_factory=dict)


class RegistrationRule:
    code: ClassVar[RuleCode]

    def defaults(self) -> RuleDefaults:
        return RuleDefaults()

    def applies_to(self, action: AttemptAction) -> bool:
        return action in ADDING

    def check(self, context: RegistrationContext, parameters: dict[str, Any]) -> RuleCheck:
        raise NotImplementedError
