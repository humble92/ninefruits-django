"""Certificate seed data (original ``KoreanUniversityProfileSeeder::certificateTypes`` and
``DemoCertificateSeeder``): three kinds with templates in Korean, English, Simplified Chinese and
Lao, created once so administrators' edits stay; the demo issues are reproducible with
``--seed`` and skipped without a PDF service."""

from __future__ import annotations

import httpx
import pytest

from ninefruits.certificate.models import CertificateIssue, CertificateTemplate, CertificateType
from ninefruits.setup.seeders.demo import DemoOptions, use_options
from ninefruits.setup.seeders.demo.accounts import DemoAccountSeeder
from ninefruits.setup.seeders.demo.certificate import DemoCertificateSeeder
from ninefruits.setup.seeders.demo.people import DemoPeopleSeeder
from ninefruits.setup.seeders.demo.reference import DemoReferenceSeeder
from ninefruits.setup.seeders.profiles.korean_university_certificates import seed_certificate_types

pytestmark = pytest.mark.django_db


def test_seeds_three_kinds_with_templates_in_four_languages_once(essential_data: None) -> None:
    seed_certificate_types()

    kinds = {kind.code: kind for kind in CertificateType.objects.all()}
    assert list(kinds) == ["ENR", "GRD", "TRN"]
    assert kinds["ENR"].audience == "enrolled"
    assert kinds["GRD"].audience == "graduated"
    assert kinds["TRN"].audience == "any" and kinds["TRN"].has_grades
    assert set(kinds["ENR"].name_translations) == {"en", "ko", "zh-hans", "lo"}
    for kind in kinds.values():
        assert set(kind.templates.values_list("locale", flat=True)) == {"en", "ko", "zh-hans", "lo"}
    template = CertificateTemplate.objects.get(certificate_type=kinds["GRD"], locale="zh-hans")
    assert "{graduation_date}" in template.body
    assert template.footer == "可通过下方二维码或网址核验本证明。"

    # Administrators' edits stay: the seeder adds nothing once kinds exist.
    template.title = "毕业证明"
    template.save()
    CertificateTemplate.objects.filter(certificate_type=kinds["TRN"], locale="lo").delete()
    seed_certificate_types()
    assert CertificateType.objects.count() == 3
    assert CertificateTemplate.objects.count() == 11
    assert CertificateTemplate.objects.get(pk=template.pk).title == "毕业证明"


def test_the_korean_university_profile_includes_the_certificate_kinds(essential_data: None) -> None:
    from ninefruits.setup.seeders.profiles.korean_university import KoreanUniversityProfileSeeder

    KoreanUniversityProfileSeeder()()
    KoreanUniversityProfileSeeder()()
    assert CertificateType.objects.count() == 3
    assert CertificateTemplate.objects.count() == 12


def _demo(seed: int) -> list[tuple[str, str, str]]:
    with use_options(DemoOptions(size="tiny", seed=seed)):
        for seeder in (DemoAccountSeeder, DemoReferenceSeeder, DemoPeopleSeeder, DemoCertificateSeeder):
            seeder()()
    return list(
        CertificateIssue.objects.order_by("pk").values_list(
            "certificate_type__code", "locale", "student_record__student_number"
        )
    )


def test_demo_issues_go_through_the_action(essential_data: None) -> None:
    issued = _demo(42)
    # tiny: the demo student's enrollment certificate, the alumnus' graduation certificate, a transcript.
    assert [code for code, _locale, _number in issued] == ["ENR", "GRD", "TRN"]
    assert CertificateIssue.objects.filter(status="revoked").count() == 1
    assert all(issue.pdf() is not None for issue in CertificateIssue.objects.all())
    # Running again adds nothing.
    with use_options(DemoOptions(size="tiny", seed=42)):
        DemoCertificateSeeder()()
    assert CertificateIssue.objects.count() == 3


def test_demo_skips_certificates_without_the_pdf_service(essential_data: None, gotenberg: object) -> None:
    gotenberg.mock(side_effect=httpx.ConnectError("refused"))  # type: ignore[attr-defined]
    assert _demo(42) == []
