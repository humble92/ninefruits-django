"""Starts a term's rule set: a copy of another term's (usually the previous one of the same
type) or the catalog defaults (original ``PrepareRuleSet``). Rules added to the catalog later
appear with defaults (``RuleCatalogSeeder`` adds their rows)."""

from __future__ import annotations

from typing import Any

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils.translation import gettext as _

from ninefruits.audit.logger import audit
from ninefruits.registration.models import RegistrationRule, RegistrationRuleSet
from ninefruits.registration.services.rule_catalog import RuleCatalog


class PrepareRuleSet:
    def __init__(self, catalog: RuleCatalog | None = None) -> None:
        self.catalog = catalog or RuleCatalog()

    def __call__(self, term: Any, copy_from: RegistrationRuleSet | None, prepared_by: Any) -> RegistrationRuleSet:
        return self.handle(term, copy_from, prepared_by)

    def handle(self, term: Any, copy_from: RegistrationRuleSet | None, prepared_by: Any) -> RegistrationRuleSet:
        if RegistrationRuleSet.objects.filter(term_id=term.pk).exists():
            raise ValidationError({"term_id": _("The term already has a rule set.")})
        with transaction.atomic():
            rule_set = RegistrationRuleSet.objects.create(
                term_id=term.pk, copied_from_rule_set_id=copy_from.pk if copy_from else None
            )
            copied = {rule.rule_code: rule for rule in copy_from.rules.all()} if copy_from else {}
            rows = []
            for rule in self.catalog.configurable():
                source = copied.get(rule.code.value)
                defaults = rule.defaults()
                parameters = source.parameters if source is not None else defaults.parameters
                rows.append(
                    RegistrationRule(
                        rule_set=rule_set,
                        rule_code=rule.code,
                        is_enabled=source.is_enabled if source is not None else True,
                        severity=source.severity if source is not None else defaults.severity,
                        allows_override=source.allows_override if source is not None else defaults.allows_override,
                        parameters=dict(parameters) if parameters else None,
                    )
                )
            RegistrationRule.objects.bulk_create(rows)
            audit(
                "registration_rule_set.prepared",
                rule_set,
                properties={"term": term.code, "copied_from": copy_from.term.code if copy_from else None},
                causer=prepared_by,
            )
        return rule_set
