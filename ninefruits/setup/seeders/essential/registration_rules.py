"""Registration rule catalog (porting-plan 10.6: "카탈로그 동기화 시더"). The catalog itself is code
(``RuleCatalog``); a term's rule set stores rows for the configurable rules. When a release adds
a rule to the catalog, existing rule sets get its row with the catalog defaults, so the rule
appears on their pages. Rows administrators changed are kept. Idempotent."""

from __future__ import annotations

from ninefruits.setup.seeders.base import Seeder


class RegistrationRuleCatalogSeeder(Seeder):
    def run(self) -> None:
        from ninefruits.registration.models import RegistrationRule, RegistrationRuleSet
        from ninefruits.registration.services.rule_catalog import RuleCatalog

        rules = RuleCatalog().configurable()
        existing = set(RegistrationRule.objects.values_list("rule_set_id", "rule_code"))
        missing = []
        for rule_set_id in RegistrationRuleSet.objects.values_list("pk", flat=True):
            for rule in rules:
                if (rule_set_id, rule.code.value) in existing:
                    continue
                defaults = rule.defaults()
                missing.append(
                    RegistrationRule(
                        rule_set_id=rule_set_id,
                        rule_code=rule.code,
                        is_enabled=True,
                        severity=defaults.severity,
                        allows_override=defaults.allows_override,
                        parameters=dict(defaults.parameters) or None,
                    )
                )
        RegistrationRule.objects.bulk_create(missing, batch_size=500)
