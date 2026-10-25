from __future__ import annotations

from collections.abc import Sequence
from datetime import date, timedelta
from typing import Any

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils.translation import gettext as _

from ninefruits.audit.logger import audit
from ninefruits.organization.enums import OrgUnitChangeType
from ninefruits.organization.models import OrgUnit, OrgUnitSuccession


class ReorganizeOrgUnit:
    """Records a reorganization: the unit ends the day before the effective date and its
    successors are linked. History is never rewritten; past records keep pointing at the old
    unit, and the succession tells which unit took over (porting-plan 10.4, ADR 0006)."""

    def __call__(
        self,
        unit: OrgUnit,
        change_type: OrgUnitChangeType | str,
        successors: Sequence[OrgUnit],
        effective_date: date,
        reason: str,
        changed_by: Any = None,
    ) -> None:
        change_type = OrgUnitChangeType(change_type)
        if not successors:
            raise ValidationError({"successors": _("Choose the successor unit.")})
        if change_type != OrgUnitChangeType.SPLIT and len(successors) > 1:
            raise ValidationError({"successors": _("Only a split can have several successors.")})
        if effective_date <= unit.effective_start_date:
            raise ValidationError({"effective_date": _("The effective date must be after the unit started.")})
        if any(successor.pk == unit.pk for successor in successors):
            raise ValidationError({"successors": _("A unit cannot succeed itself.")})

        with transaction.atomic():
            last_day = effective_date - timedelta(days=1)
            if unit.effective_end_date is None or unit.effective_end_date > last_day:
                unit.effective_end_date = last_day
                unit.save(update_fields=["effective_end_date", "updated_at"])
            for successor in successors:
                OrgUnitSuccession.objects.update_or_create(
                    predecessor=unit,
                    successor=successor,
                    defaults={"change_type": change_type, "effective_date": effective_date, "reason": reason},
                )
            audit(
                "org_unit.reorganized",
                unit,
                reason=reason,
                properties={
                    "change_type": change_type.value,
                    "successor_ids": [successor.pk for successor in successors],
                    "effective_date": effective_date.isoformat(),
                },
                causer=changed_by,
            )
