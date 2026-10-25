from __future__ import annotations

from typing import Any

from django.utils.translation import gettext as _

from ninefruits.registration.data import RegistrationContext, RuleCheck
from ninefruits.registration.enums import HoldType, RuleCode

from .base import RegistrationRule, RuleDefaults


class HoldRule(RegistrationRule):
    """Holds that block registration (legacy SRDENY). The message names the hold type, never the
    internal reason."""

    code = RuleCode.HOLD

    def defaults(self) -> RuleDefaults:
        return RuleDefaults(allows_override=False)

    def check(self, context: RegistrationContext, parameters: dict[str, Any]) -> RuleCheck:
        from ninefruits.registration.models import RegistrationHold

        hold = (
            RegistrationHold.objects.filter(student_record_id=context.record.pk, blocks_registration=True)
            .in_force(context.at)
            .order_by("id")
            .first()
        )
        if hold is None:
            return RuleCheck.ok()
        return RuleCheck.fail(
            _("You have a hold (%(type)s). Contact the office that placed it.")
            % {"type": HoldType(hold.hold_type).label},
            {"hold_id": hold.pk},
        )
