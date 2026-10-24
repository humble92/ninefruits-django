"""Checks a term before registration opens (original ``registration:preflight``,
porting-plan 13.1): windows, rule set, sections, seats, credit limits, holds. Read only."""

from __future__ import annotations

from typing import Any

from django.core.management.base import CommandParser
from django.db.models import Q

from ninefruits.core.commands import StatusCommand
from ninefruits.core.db import session_context
from ninefruits.offering.enums import SectionStatus
from ninefruits.offering.models import Section
from ninefruits.person.enums import StudentStatus
from ninefruits.person.models import StudentRecord
from ninefruits.registration.models import CreditLimitPolicy, RegistrationHold, RegistrationRuleSet
from ninefruits.registration.services.rule_catalog import RuleCatalog
from ninefruits.term.enums import TermWindowType
from ninefruits.term.models import Term, TermWindow


class Command(StatusCommand):
    help = "Check a term before registration opens: windows, rule set, sections, seats, credit limits, holds"

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument("term", help="Term code, e.g. 2027-SP")

    def handle(self, *args: Any, **options: Any) -> int:
        # Reads every student record: as the system (row level security).
        with session_context().system("command:registration_preflight"):
            return self._check(options)

    def _check(self, options: dict[str, Any]) -> int:
        term = Term.objects.filter(code=options["term"]).first()
        if term is None:
            self.error("Unknown term code.")
            return self.FAILURE

        problems: list[str] = []
        info: list[str] = []
        windows = list(TermWindow.objects.filter(term=term).values_list("window_type", flat=True))
        for window_type in (TermWindowType.REGISTRATION, TermWindowType.ADD_DROP):
            count = windows.count(window_type.value)
            if count == 0:
                problems.append(f"No {window_type.value} window.")
            else:
                info.append(f"{count} {window_type.value} window(s).")

        rule_set = RegistrationRuleSet.objects.filter(term=term).first()
        if rule_set is None:
            info.append(f"No rule set: catalog defaults apply ({len(RuleCatalog().all())} rules).")
        else:
            info.append(f"Rule set with {rule_set.rules.filter(is_enabled=True).count()} enabled rule(s).")

        sections = list(
            Section.objects.filter(term=term)
            .select_related("course", "version", "session")
            .prefetch_related("seat_groups")
        )
        published = [s for s in sections if s.status == SectionStatus.PUBLISHED]
        drafts = [s for s in sections if s.status == SectionStatus.DRAFT]
        info.append(f"{len(published)} published section(s), {len(drafts)} draft(s).")
        for section in published:
            if section.capacity == 0:
                problems.append(f"{section.label()}: capacity 0.")
            if sum(group.capacity for group in section.seat_groups.all()) > section.capacity:
                problems.append(f"{section.label()}: seat groups exceed the capacity.")
            if not section.version.is_effective_on(section.session.start_date):
                problems.append(f"{section.label()}: course version not in effect at the session start.")

        policies = list(
            CreditLimitPolicy.objects.filter(is_active=True)
            .filter(Q(term_type_id__isnull=True) | Q(term_type_id=term.term_type_id))
            .order_by("-priority", "id")
        )
        unlimited = sum(
            1
            for record in StudentRecord.objects.filter(status=StudentStatus.ENROLLED).iterator(chunk_size=2000)
            if not any(policy.eligibility.matches(record) for policy in policies)
        )
        if unlimited:
            problems.append(f"{unlimited} enrolled student(s) match no credit limit policy (no limit).")

        held = (
            RegistrationHold.objects.filter(blocks_registration=True)
            .in_force()
            .values("student_record_id")
            .distinct()
            .count()
        )
        info.append(f"{held} student(s) with a hold blocking registration.")

        for line in info:
            self.info(line)
        for line in problems:
            self.warn(line)
        return self.PROBLEMS_FOUND if problems else self.SUCCESS
