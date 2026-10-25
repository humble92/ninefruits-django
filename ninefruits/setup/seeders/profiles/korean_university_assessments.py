"""Examination kinds of the Korean university profile (original
``KoreanUniversityProfileSeeder::assessmentTypes``; legacy CET types, SSCORE_ADD exams, COMEXAM):
an in-house English comprehensive exam with four areas, a computer exam and the thesis as
pass/fail, and TOPIK as an external test with a level.

A ``LATER_PHASE_STEPS`` entry of ``KoreanUniversityProfileSeeder``. Idempotent: kinds are found by
code and keep what administrators changed (missing translations are added); the areas are created
with their kind only, so areas an administrator removed stay removed."""

from __future__ import annotations

from typing import Any

from ninefruits.assessment.models import AssessmentComponent, AssessmentType
from ninefruits.setup.seeders.base import seed_row

ENGLISH_AREAS = [
    ("LISTENING", {"en": "Listening", "ko": "듣기", "zh-hans": "听力", "lo": "ການຟັງ"}),
    ("READING", {"en": "Reading", "ko": "읽기", "zh-hans": "阅读", "lo": "ການອ່ານ"}),
    ("WRITING", {"en": "Writing", "ko": "쓰기", "zh-hans": "写作", "lo": "ການຂຽນ"}),
    ("GRAMMAR", {"en": "Grammar", "ko": "문법", "zh-hans": "语法", "lo": "ໄວຍາກອນ"}),
]

KINDS: list[tuple[str, dict[str, str], dict[str, Any]]] = [
    (
        "ENG_COMP",
        {
            "en": "English comprehensive examination",
            "ko": "영어종합시험",
            "zh-hans": "英语综合考试",
            "lo": "ການສອບເສັງພາສາອັງກິດລວມ",
        },
        {"category": "language", "scoring": "score", "pass_score": 60, "sort_order": 10},
    ),
    (
        "COMP_EXAM",
        {
            "en": "Computer comprehensive examination",
            "ko": "전산종합시험",
            "zh-hans": "计算机综合考试",
            "lo": "ການສອບເສັງຄອມພິວເຕີລວມ",
        },
        {"category": "comprehensive", "scoring": "pass_fail", "sort_order": 20},
    ),
    (
        "THESIS",
        {"en": "Graduation thesis", "ko": "졸업논문", "zh-hans": "毕业论文", "lo": "ບົດວິທະຍານິພົນຈົບການສຶກສາ"},
        {"category": "thesis", "scoring": "pass_fail", "sort_order": 30},
    ),
    (
        "TOPIK",
        {
            "en": "TOPIK (Test of Proficiency in Korean)",
            "ko": "한국어능력시험(TOPIK)",
            "zh-hans": "韩国语能力考试（TOPIK）",
            "lo": "ການສອບເສັງຄວາມສາມາດພາສາເກົາຫຼີ (TOPIK)",
        },
        {"category": "external", "scoring": "pass_fail", "allows_external": True, "sort_order": 40},
    ),
]


def seed_assessment_types(seeder: Any = None) -> None:
    for code, name, attributes in KINDS:
        created = not AssessmentType.objects.filter(code=code).exists()
        kind = seed_row(AssessmentType, {"code": code}, {"name": name}, attributes)
        if created and code == "ENG_COMP":
            AssessmentComponent.objects.bulk_create(
                AssessmentComponent(
                    assessment_type=kind, code=area, name=area_name, max_score=25, sort_order=(index + 1) * 10
                )
                for index, (area, area_name) in enumerate(ENGLISH_AREAS)
            )
