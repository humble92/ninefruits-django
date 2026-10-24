"""Registration part of the ``yust-legacy`` profile (original ``YustLegacyProfileSeeder``,
Phase 5): credit limits by term type, admission year and nursing, and credit bank courses
(codes ``009*``, ``900*``) outside the limit. Idempotent: policies are found by English name and
term type and updated, so running the profile again repairs them. The legacy bug that limited
nursing students from 2014 to 18 credits instead of 21 is not reproduced."""

from __future__ import annotations

from typing import Any

from django.db.models import Q

from ninefruits.core.targeting import TargetCriteria

#: (name, term types, eligibility, max credits, priority, needs a nursing unit)
POLICIES: list[tuple[str, tuple[str, ...], dict[str, Any], int, int, bool]] = [
    (
        "Regular 2014+ nursing",
        ("spring", "fall"),
        {"admission_year_from": 2014, "org_unit_ids": "nursing"},
        21,
        40,
        True,
    ),
    ("Regular 2014+", ("spring", "fall"), {"admission_year_from": 2014}, 18, 30, False),
    ("Regular 2013- nursing", ("spring", "fall"), {"admission_year_to": 2013, "org_unit_ids": "nursing"}, 20, 20, True),
    ("Regular 2013-", ("spring", "fall"), {"admission_year_to": 2013}, 17, 10, False),
    (
        "Seasonal 2014+ nursing",
        ("summer", "winter"),
        {"admission_year_from": 2014, "org_unit_ids": "nursing"},
        6,
        40,
        True,
    ),
    ("Seasonal 2014+", ("summer", "winter"), {"admission_year_from": 2014}, 5, 30, False),
    ("Seasonal 2013-", ("summer", "winter"), {"admission_year_to": 2013}, 6, 10, False),
]


def seed_registration_rules(profile: Any) -> None:
    """``LATER_PHASE_STEPS`` entry of ``YustLegacyProfileSeeder``."""
    from ninefruits.curriculum.models import CourseVersion
    from ninefruits.organization.models import OrgUnit
    from ninefruits.registration.models import CreditLimitPolicy
    from ninefruits.term.models import TermType

    types = dict(TermType.objects.values_list("code", "pk"))
    nursing = list(OrgUnit.objects.filter(code__in=profile.NURSING_UNIT_CODES).values_list("pk", flat=True))

    for name, term_types, eligibility, maximum, priority, needs_nursing in POLICIES:
        if needs_nursing and not nursing:
            continue
        criteria = TargetCriteria.from_dict(
            {key: (nursing if value == "nursing" else value) for key, value in eligibility.items()}
        )
        for code in term_types:
            if code not in types:
                continue
            label = f"{name} ({code})"
            policy = next(
                (
                    candidate
                    for candidate in CreditLimitPolicy.objects.filter(term_type_id=types[code])
                    if candidate.name_translations.get("en") == label
                ),
                None,
            ) or CreditLimitPolicy(term_type_id=types[code])
            policy.name = {"en": label}
            policy.eligibility = criteria
            policy.max_credits = maximum
            policy.priority = priority
            policy.save()

    CourseVersion.objects.filter(Q(course__code__startswith="009") | Q(course__code__startswith="900")).update(
        counts_toward_credit_limit=False
    )
