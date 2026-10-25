"""The examination kinds of the Korean university profile (original
``KoreanUniversityProfileSeeder::assessmentTypes``) and the demo examinations: the profile is
idempotent and keeps what administrators changed; the demo seeds once and deterministically."""

from __future__ import annotations

from decimal import Decimal

import pytest

from ninefruits.assessment.enums import ScoringMethod
from ninefruits.assessment.models import AssessmentComponent, AssessmentResult, AssessmentSession, AssessmentType
from ninefruits.setup.seeders.demo import DemoOptions, use_options
from ninefruits.setup.seeders.demo.accounts import DemoAccountSeeder
from ninefruits.setup.seeders.demo.assessment import DemoAssessmentSeeder
from ninefruits.setup.seeders.demo.curriculum import DemoCurriculumSeeder
from ninefruits.setup.seeders.demo.people import DemoPeopleSeeder
from ninefruits.setup.seeders.demo.reference import DemoReferenceSeeder
from ninefruits.setup.seeders.profiles.korean_university import KoreanUniversityProfileSeeder

pytestmark = pytest.mark.django_db


def test_seeds_the_four_kinds_once_and_keeps_what_administrators_changed(profile: None) -> None:
    assert list(AssessmentType.objects.order_by("sort_order").values_list("code", flat=True)) == [
        "ENG_COMP",
        "COMP_EXAM",
        "THESIS",
        "TOPIK",
    ]
    english = AssessmentType.objects.get(code="ENG_COMP")
    assert english.scoring == ScoringMethod.SCORE
    assert english.pass_score == Decimal("60.0")
    assert list(english.components.values_list("code", flat=True)) == ["LISTENING", "READING", "WRITING", "GRAMMAR"]
    assert english.name_translations["ko"] == "영어종합시험"
    assert AssessmentType.objects.get(code="TOPIK").allows_external is True

    english.pass_score = Decimal(70)
    english.save()
    english.components.get(code="GRAMMAR").delete()
    KoreanUniversityProfileSeeder()()

    english.refresh_from_db()
    assert AssessmentType.objects.count() == 4
    assert english.pass_score == Decimal("70.0")
    assert AssessmentComponent.objects.filter(assessment_type=english).count() == 3


def test_seeds_the_demo_examinations_once(profile: None) -> None:
    with use_options(DemoOptions(size="tiny", seed=7)):
        for seeder in (DemoAccountSeeder, DemoReferenceSeeder, DemoPeopleSeeder, DemoCurriculumSeeder):
            seeder()()
        DemoAssessmentSeeder()()
        sessions, results = AssessmentSession.objects.count(), AssessmentResult.objects.count()
        DemoAssessmentSeeder()()
    assert (sessions, AssessmentSession.objects.count()) == (4, 4)
    assert AssessmentResult.objects.count() == results
    # Stored decisions follow the rule: total at or above 60 (no area minimums in the profile).
    for result in AssessmentResult.objects.filter(session__assessment_type__code="ENG_COMP"):
        assert result.is_passed == (result.total_score >= 60)
        assert sum(score.score for score in result.component_scores.all()) == result.total_score
