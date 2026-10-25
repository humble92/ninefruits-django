"""Original tests/Feature/Setup/ReferenceSeedersTest.php."""

from __future__ import annotations

from io import StringIO

import pytest
from django.core.management import call_command

from ninefruits.curriculum.models import CourseCategory
from ninefruits.grading.models import GradeScale
from ninefruits.institution.models import Country, Language, LookupType
from ninefruits.organization.models import OrgUnit
from ninefruits.security.actions import AssignRole
from ninefruits.security.models import Role
from ninefruits.setup.seeders.essential import EssentialSeeder
from ninefruits.setup.seeders.profiles.korean_university import KoreanUniversityProfileSeeder
from ninefruits.term.enums import TermWindowType
from ninefruits.term.models import Term, TermType
from ninefruits.term.services import TermResolver
from tests.factories.security import UserFactory

pytestmark = pytest.mark.django_db


def test_seeds_iso_countries_and_languages_with_names_in_every_installed_language() -> None:
    EssentialSeeder()()

    korea = Country.objects.get(code="KR")
    assert Country.objects.count() == 249
    assert korea.alpha3_code == "KOR"
    assert korea.numeric_code == "410"
    assert {"en", "ko", "zh-hans", "lo"} <= set(korea.name_translations)
    assert Language.objects.get(code="ko").name_translations["zh-hans"] == "韩语"
    assert Language.objects.count() == 184
    assert sorted(LookupType.objects.filter(is_system=True).values_list("code", flat=True)) == [
        "admission_type",
        "application_document_type",
        "ethnicity",
        "room_type",
    ]


def test_keeps_administrator_edits_and_only_adds_missing_translations_when_run_again() -> None:
    EssentialSeeder()()
    korea = Country.objects.get(code="KR")
    korea.name = {"en": "South Korea"}
    korea.save()

    EssentialSeeder()()

    korea.refresh_from_db()
    assert Country.objects.count() == 249
    assert korea.name_translations["en"] == "South Korea"
    assert korea.name_translations["ko"] == "대한민국"


def test_applies_the_korean_university_profile_idempotently() -> None:
    EssentialSeeder()()
    KoreanUniversityProfileSeeder()()
    KoreanUniversityProfileSeeder()()

    scale = GradeScale.objects.get(code="KR45")
    items = list(scale.items.order_by("sort_order"))
    assert sorted(TermType.objects.values_list("code", flat=True)) == ["fall", "spring", "summer", "winter"]
    assert scale.is_default
    assert [item.code for item in items] == ["A+", "A0", "B+", "B0", "C+", "C0", "D+", "D0", "F", "P", "NP"]
    assert not next(item for item in items if item.code == "P").counts_in_gpa
    assert CourseCategory.objects.get(code="MAJ_REQ").parent.code == "MAJ"


@pytest.mark.django_db(databases=["default", "migrator"])
def test_applies_profiles_chosen_in_setup_install() -> None:
    EssentialSeeder()()
    AssignRole()(UserFactory(), Role.objects.get(name="system_administrator"), "test")

    assert call_command("setup_install", force=True, profile=["korean-university"], stdout=StringIO()) == 0

    assert GradeScale.objects.filter(code="KR45").exists()


def test_builds_a_demo_calendar_that_matches_the_term_resolver() -> None:
    EssentialSeeder()()
    assert call_command("setup_demo", force=True, stdout=StringIO()) == 0
    assert call_command("setup_demo", force=True, stdout=StringIO()) == 0

    resolver = TermResolver()
    assert Term.objects.count() == 3
    assert OrgUnit.objects.filter(code="DEMO").count() == 1
    assert len(resolver.terms_open_for(TermWindowType.REGISTRATION_CART)) == 1
    assert [window.eligibility.year_levels for window in resolver.open_windows(TermWindowType.REGISTRATION)] == [[4]]
