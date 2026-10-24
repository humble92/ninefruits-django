"""Runs every applicable rule and collects all results (original ``RegistrationRuleEngine``,
porting-plan 10.6).

Per rule the term's rule set decides: enabled, block or warn, override allowed, parameters.
Without a rule set (or a row for the rule) the catalog defaults apply. A failed rule is
overridden when overrides are allowed and staff waived it for this action (staff never need the
window) or the student has an override in force for the term (and section or course). Seats are
not a rule: they are taken atomically afterwards (``SeatAllocator``)."""

from __future__ import annotations

from typing import Any

from django.db.models import Prefetch

from ninefruits.registration.data import RegistrationContext, RuleEvaluation, RuleResult
from ninefruits.registration.enums import RuleCode, RuleSeverity

from .rule_catalog import RuleCatalog


class RegistrationRuleEngine:
    def __init__(self, catalog: RuleCatalog | None = None) -> None:
        self.catalog = catalog or RuleCatalog()
        self._configurations: dict[int, dict[str, Any]] = {}

    def evaluate(self, context: RegistrationContext) -> RuleEvaluation:
        from ninefruits.offering.models import Section, SectionMeeting
        from ninefruits.registration.models import RegistrationOverride

        # Callers pass sections loaded for their screens; the rules need these.
        section = context.section
        loaded = (
            Section.objects.select_related("course", "version", "term", "session")
            .prefetch_related(Prefetch("meetings", queryset=SectionMeeting.objects.all()))
            .get(pk=section.pk)
        )
        for name in ("course", "version", "term", "session"):
            section._state.fields_cache[name] = getattr(loaded, name)
        section._prefetched_objects_cache = {
            **getattr(section, "_prefetched_objects_cache", {}),
            "meetings": loaded.meetings.all(),
        }

        configuration = self._configuration(section.term_id)
        overrides = [
            override
            for override in RegistrationOverride.objects.filter(
                student_record_id=context.record.pk, term_id=section.term_id
            ).in_force(context.at)
            if override.covers(section)
        ]
        results: list[RuleResult] = []
        for rule in self.catalog.all():
            code = rule.code
            configured = configuration.get(code.value)
            if not rule.applies_to(context.action):
                continue
            if not code.is_core() and configured is not None and not configured.is_enabled:
                continue
            defaults = rule.defaults()
            if code.is_core() or configured is None:
                severity = RuleSeverity.BLOCK if code.is_core() else defaults.severity
                allows_override = defaults.allows_override
                parameters = dict(defaults.parameters)
            else:
                severity = RuleSeverity(configured.severity)
                allows_override = configured.allows_override
                parameters = {**defaults.parameters, **(configured.parameters or {})}

            check = rule.check(context, parameters)
            overridden = (
                not check.passed
                and allows_override
                and (
                    code in context.waived
                    or (code == RuleCode.WINDOW and context.by_staff)
                    or any(override.rule_code == code for override in overrides)
                )
            )
            results.append(RuleResult(code, check.passed, severity, overridden, check.message, check.details))
        return RuleEvaluation(tuple(results))

    def _configuration(self, term_id: int) -> dict[str, Any]:
        from ninefruits.registration.models import RegistrationRule

        if term_id not in self._configurations:
            self._configurations[term_id] = {
                rule.rule_code: rule for rule in RegistrationRule.objects.filter(rule_set__term_id=term_id)
            }
        return self._configurations[term_id]
