"""Typical Korean four-year university (original ``KoreanUniversityProfileSeeder``)."""

from __future__ import annotations

from datetime import time
from decimal import Decimal
from typing import Any

from ninefruits.curriculum.models import CourseCategory
from ninefruits.grading.models import GradeScale, GradeScaleItem
from ninefruits.institution.models import LookupType, LookupValue
from ninefruits.setup.seeders.base import seed_row
from ninefruits.setup.seeders.essential.lookup_type import (
    ADMISSION_TYPE_LOOKUP,
    DOCUMENT_TYPE_LOOKUP,
    ROOM_TYPE_LOOKUP,
    LookupTypeSeeder,
)
from ninefruits.setup.seeders.profiles import SetupProfile
from ninefruits.term.models import TermType, TimeSlot

#: code -> (points, min %, max %, counts in GPA, passing[, applies to])
ScaleItems = dict[str, tuple[Any, ...]]


class KoreanUniversityProfileSeeder(SetupProfile):
    """Spring/summer/fall/winter terms, general education and major categories, a 4.5 grade
    scale, 50-minute periods from 09:00, common room types, admission types and application
    documents. Idempotent; values administrators changed are kept.

    The original profile also creates the standard course evaluation form, certificate types
    and examination types; those steps join this seeder with their phases (7, 8 and 9) in
    ``LATER_PHASE_STEPS``."""

    key = "korean-university"
    label = "Korean university"
    description = (
        "Spring/summer/fall/winter terms, 4.5 grade scale, course categories, periods from 09:00, room types, "
        "admission types and application documents"
    )

    #: Dotted paths of functions ``(seeder) -> None`` added by later phases.
    LATER_PHASE_STEPS: list[str] = [
        "ninefruits.setup.seeders.profiles.korean_university_evaluation.seed_evaluation_form",
        # Phase 8: certificate kinds and their templates in four languages.
        "ninefruits.setup.seeders.profiles.korean_university_certificates.seed_certificate_types",
        # Phase 9: examination kinds and the English exam's areas.
        "ninefruits.setup.seeders.profiles.korean_university_assessments.seed_assessment_types",
    ]

    def run(self) -> None:
        self.call(LookupTypeSeeder)
        self.term_types()
        self.course_categories()
        self.grade_scale()
        self.time_slots()
        self.room_types()
        self.lookup_values(
            ADMISSION_TYPE_LOOKUP,
            {
                "freshman": {"en": "Freshman admission", "ko": "신입학", "zh-hans": "新生入学", "lo": "ການຮັບເຂົ້າຮຽນໃໝ່"},
                "transfer": {"en": "Transfer admission", "ko": "편입학", "zh-hans": "插班入学", "lo": "ການຮັບຍ້າຍເຂົ້າຮຽນ"},
                "readmission": {"en": "Readmission", "ko": "재입학", "zh-hans": "重新入学", "lo": "ການຮັບເຂົ້າຮຽນຄືນ"},
                "international": {
                    "en": "International student admission",
                    "ko": "외국인 특별전형",
                    "zh-hans": "外国留学生入学",
                    "lo": "ການຮັບນັກສຶກສາຕ່າງປະເທດ",
                },
            },
        )
        self.lookup_values(
            DOCUMENT_TYPE_LOOKUP,
            {
                "diploma": {
                    "en": "Diploma or certificate of expected graduation",
                    "ko": "졸업(예정)증명서",
                    "zh-hans": "毕业（预计毕业）证明",
                    "lo": "ໃບຢັ້ງຢືນການຈົບການສຶກສາ (ຫຼື ຄາດວ່າຈະຈົບ)",
                },
                "transcript": {"en": "Transcript", "ko": "성적증명서", "zh-hans": "成绩证明", "lo": "ໃບຄະແນນ"},
                "identity": {
                    "en": "Copy of ID or passport",
                    "ko": "신분증 또는 여권 사본",
                    "zh-hans": "身份证或护照复印件",
                    "lo": "ສຳເນົາບັດປະຈຳຕົວ ຫຼື ໜັງສືຜ່ານແດນ",
                },
                "language_test": {
                    "en": "Language test score",
                    "ko": "어학 성적",
                    "zh-hans": "语言成绩",
                    "lo": "ຄະແນນສອບພາສາ",
                },
            },
        )
        from django.utils.module_loading import import_string

        for path in self.LATER_PHASE_STEPS:
            import_string(path)(self)

    def term_types(self) -> None:
        types = {
            "spring": (10, True, {"en": "Spring term", "ko": "1학기", "zh-hans": "春季学期", "lo": "ພາກຮຽນທີ 1"}),
            "summer": (
                20,
                False,
                {"en": "Summer session", "ko": "여름 계절학기", "zh-hans": "夏季学期", "lo": "ພາກຮຽນລະດູຮ້ອນ"},
            ),
            "fall": (30, True, {"en": "Fall term", "ko": "2학기", "zh-hans": "秋季学期", "lo": "ພາກຮຽນທີ 2"}),
            "winter": (
                40,
                False,
                {"en": "Winter session", "ko": "겨울 계절학기", "zh-hans": "冬季学期", "lo": "ພາກຮຽນລະດູໜາວ"},
            ),
        }
        for code, (sort_order, is_regular, name) in types.items():
            seed_row(TermType, {"code": code}, {"name": name}, {"sort_order": sort_order, "is_regular": is_regular})

    def course_categories(self) -> None:
        groups: dict[str, tuple[int, dict[str, str], dict[str, dict[str, str]]]] = {
            "GE": (
                10,
                {"en": "General education", "ko": "교양", "zh-hans": "通识教育", "lo": "ວິຊາສຶກສາທົ່ວໄປ"},
                {
                    "GE_REQ": {
                        "en": "General education required",
                        "ko": "교양필수",
                        "zh-hans": "通识必修",
                        "lo": "ວິຊາສຶກສາທົ່ວໄປບັງຄັບ",
                    },
                    "GE_ELEC": {
                        "en": "General education elective",
                        "ko": "교양선택",
                        "zh-hans": "通识选修",
                        "lo": "ວິຊາສຶກສາທົ່ວໄປເລືອກ",
                    },
                },
            ),
            "MAJ": (
                20,
                {"en": "Major", "ko": "전공", "zh-hans": "专业", "lo": "ວິຊາສາຂາ"},
                {
                    "MAJ_FND": {
                        "en": "Major foundation",
                        "ko": "전공기초",
                        "zh-hans": "专业基础",
                        "lo": "ວິຊາສາຂາພື້ນຖານ",
                    },
                    "MAJ_REQ": {"en": "Major required", "ko": "전공필수", "zh-hans": "专业必修", "lo": "ວິຊາສາຂາບັງຄັບ"},
                    "MAJ_ELEC": {"en": "Major elective", "ko": "전공선택", "zh-hans": "专业选修", "lo": "ວິຊາສາຂາເລືອກ"},
                },
            ),
            "FREE": (30, {"en": "Free elective", "ko": "일반선택", "zh-hans": "任意选修", "lo": "ວິຊາເລືອກເສລີ"}, {}),
        }
        for code, (sort_order, name, children) in groups.items():
            parent = seed_row(CourseCategory, {"code": code}, {"name": name}, {"sort_order": sort_order})
            child_order = sort_order
            for child_code, child_name in children.items():
                child_order += 1
                seed_row(
                    CourseCategory,
                    {"code": child_code},
                    {"name": child_name},
                    {"parent": parent, "sort_order": child_order},
                )

    def grade_scale(self) -> None:
        """The 4.5 scale, the institution's scale unless one is fixed already (the scale is
        fixed at installation: ``setup_install --grade-scale``, or the first profile's scale)."""
        seed_scale_45(True)

    def time_slots(self) -> None:
        for period in range(1, 11):
            seed_row(
                TimeSlot,
                {"code": str(period)},
                {
                    "name": {
                        "en": f"Period {period}",
                        "ko": f"{period}교시",
                        "zh-hans": f"第{period}节",
                        "lo": f"ຊົ່ວໂມງທີ {period}",
                    }
                },
                {
                    "start_time": time(8 + period, 0),
                    "end_time": time(8 + period, 50),
                    "weekdays": [1, 2, 3, 4, 5],
                    "sort_order": period,
                },
            )

    def room_types(self) -> None:
        self.lookup_values(
            ROOM_TYPE_LOOKUP,
            {
                "lecture": {"en": "Lecture room", "ko": "강의실", "zh-hans": "教室", "lo": "ຫ້ອງບັນຍາຍ"},
                "laboratory": {"en": "Laboratory", "ko": "실험실", "zh-hans": "实验室", "lo": "ຫ້ອງທົດລອງ"},
                "practice": {"en": "Practice room", "ko": "실습실", "zh-hans": "实训室", "lo": "ຫ້ອງຝຶກປະຕິບັດ"},
                "seminar": {"en": "Seminar room", "ko": "세미나실", "zh-hans": "研讨室", "lo": "ຫ້ອງສຳມະນາ"},
                "auditorium": {"en": "Auditorium", "ko": "강당", "zh-hans": "礼堂", "lo": "ຫໍປະຊຸມ"},
            },
        )

    def lookup_values(self, type_code: str, values: dict[str, dict[str, str]]) -> None:
        lookup_type = LookupType.objects.get(code=type_code)
        order = 0
        for code, name in values.items():
            order += 10
            seed_row(LookupValue, {"lookup_type": lookup_type, "code": code}, {"name": name}, {"sort_order": order})


def seed_scale_45(is_default: bool) -> GradeScale:
    """The 4.5 scale (default only while the installation has no scale yet)."""
    return seed_scale(
        "KR45",
        {"en": "4.5 scale", "ko": "4.5 만점", "zh-hans": "4.5 分制", "lo": "ລະບົບ 4.5 ຄະແນນ"},
        Decimal("4.5"),
        is_default,
        {
            "A+": (4.5, 95, 100, True, True),
            "A0": (4.0, 90, 94.99, True, True),
            "B+": (3.5, 85, 89.99, True, True),
            "B0": (3.0, 80, 84.99, True, True),
            "C+": (2.5, 75, 79.99, True, True),
            "C0": (2.0, 70, 74.99, True, True),
            "D+": (1.5, 65, 69.99, True, True),
            "D0": (1.0, 60, 64.99, True, True),
            "F": (0.0, 0, 59.99, True, False),
            "P": (None, None, None, False, True),
            "NP": (None, None, None, False, False),
        },
    )


def seed_scale_43(is_default: bool) -> GradeScale:
    """The 4.3 scale with minus grades, for installations that choose it."""
    return seed_scale(
        "KR43",
        {"en": "4.3 scale", "ko": "4.3 만점", "zh-hans": "4.3 分制", "lo": "ລະບົບ 4.3 ຄະແນນ"},
        Decimal("4.3"),
        is_default,
        scale_43({"P": (True,), "NP": (False,)}),
    )


def scale_43(non_gpa: dict[str, tuple[Any, ...]]) -> ScaleItems:
    """4.3 grades with three-point score ranges, plus the given non-GPA grades
    (code -> (passing[, applies to]))."""
    items = {
        "A+": (4.3, 97, 100),
        "A0": (4.0, 93, 96.99),
        "A-": (3.7, 90, 92.99),
        "B+": (3.3, 87, 89.99),
        "B0": (3.0, 83, 86.99),
        "B-": (2.7, 80, 82.99),
        "C+": (2.3, 77, 79.99),
        "C0": (2.0, 73, 76.99),
        "C-": (1.7, 70, 72.99),
        "D+": (1.3, 67, 69.99),
        "D0": (1.0, 63, 66.99),
        "D-": (0.7, 60, 62.99),
        "F": (0.0, 0, 59.99),
    }
    rows: ScaleItems = {code: (points, low, high, True, code != "F") for code, (points, low, high) in items.items()}
    for code, options in non_gpa.items():
        rows[code] = (None, None, None, False, options[0], options[1] if len(options) > 1 else "pass_fail")
    return rows


def seed_scale(code: str, name: dict[str, str], max_points: Decimal, is_default: bool, items: ScaleItems) -> GradeScale:
    """Creates the scale and its missing grades; existing grades and scales are not changed. A
    new default is only set when no scale is the default yet (the scale is fixed)."""

    def decimal(value: Any) -> Decimal | None:
        return None if value is None else Decimal(str(value))

    scale, _created = GradeScale.objects.get_or_create(
        code=code,
        defaults={
            "name": name,
            "max_grade_points": max_points,
            "is_default": is_default and not GradeScale.objects.filter(is_default=True).exists(),
        },
    )
    order = 0
    for item_code, item in items.items():
        points, low, high, counts_in_gpa, is_passing = item[:5]
        order += 10
        GradeScaleItem.objects.get_or_create(
            grade_scale=scale,
            code=item_code,
            defaults={
                "grade_points": decimal(points),
                "min_percentage": decimal(low),
                "max_percentage": decimal(high),
                "counts_in_gpa": counts_in_gpa,
                "is_passing": is_passing,
                "applies_to": item[5] if len(item) > 5 else ("graded" if counts_in_gpa else "pass_fail"),
                "sort_order": order,
            },
        )
    return scale
