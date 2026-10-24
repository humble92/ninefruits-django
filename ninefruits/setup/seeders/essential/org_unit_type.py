from __future__ import annotations

from ninefruits.organization.models import OrgUnitType
from ninefruits.setup.seeders.base import Seeder, seed_row


class OrgUnitTypeSeeder(Seeder):
    """Default org unit types. Institutions can rename them or add more."""

    TYPES: dict[str, tuple[int, bool, dict[str, str]]] = {
        "university": (10, True, {"en": "University", "ko": "대학교", "zh-hans": "大学", "lo": "ມະຫາວິທະຍາໄລ"}),
        "college": (20, True, {"en": "College", "ko": "단과대학", "zh-hans": "学院", "lo": "ຄະນະ"}),
        "department": (30, True, {"en": "Department", "ko": "학과", "zh-hans": "系", "lo": "ພາກວິຊາ"}),
        "major": (40, True, {"en": "Major", "ko": "전공", "zh-hans": "专业", "lo": "ສາຂາວິຊາ"}),
        "office": (
            90,
            False,
            {"en": "Administrative office", "ko": "행정 부서", "zh-hans": "行政部门", "lo": "ຫ້ອງການບໍລິຫານ"},
        ),
    }

    def run(self) -> None:
        for code, (sort_order, is_academic, name) in self.TYPES.items():
            seed_row(
                OrgUnitType,
                {"code": code},
                {"name": name},
                {"sort_order": sort_order, "is_academic": is_academic},
            )
