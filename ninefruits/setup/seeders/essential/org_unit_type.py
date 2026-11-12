from __future__ import annotations

from ninefruits.organization.models import OrgUnitType
from ninefruits.setup.seeders.base import Seeder, seed_row


class OrgUnitTypeSeeder(Seeder):
    """Default org unit types. Institutions can rename them or add more."""

    TYPES: dict[str, tuple[int, bool, dict[str, str]]] = {
        "university": (
            10,
            True,
            {
                "en": "University",
                "ko": "대학교",
                "zh-hans": "大学",
                "lo": "ມະຫາວິທະຍາໄລ",
                "de": "Universität",
                "ru": "Университет",
                "ms": "Universiti",
                "fil": "Unibersidad",
                "fr": "Université",
                "ja": "大学",
                "mn": "Их сургууль",
                "ne": "विश्वविद्यालय",
                "th": "มหาวิทยาลัย",
                "tr": "Üniversite",
                "uz": "Universitet",
                "vi": "Trường đại học",
            },
        ),
        "college": (
            20,
            True,
            {
                "en": "College",
                "ko": "단과대학",
                "zh-hans": "学院",
                "lo": "ຄະນະ",
                "de": "Fakultät",
                "ru": "Институт",
                "ms": "Fakulti",
                "fil": "Kolehiyo",
                "fr": "Faculté",
                "ja": "学部",
                "mn": "Бүрэлдэхүүн сургууль",
                "ne": "सङ्काय",
                "th": "คณะ",
                "tr": "Fakülte",
                "uz": "Fakultet",
                "vi": "Trường thành viên",
            },
        ),
        "department": (
            30,
            True,
            {
                "en": "Department",
                "ko": "학과",
                "zh-hans": "系",
                "lo": "ພາກວິຊາ",
                "de": "Institut",
                "ru": "Кафедра",
                "ms": "Jabatan",
                "fil": "Departamento",
                "fr": "Département",
                "ja": "学科",
                "mn": "Тэнхим",
                "ne": "विभाग",
                "th": "ภาควิชา",
                "tr": "Bölüm",
                "uz": "Kafedra",
                "vi": "Khoa",
            },
        ),
        "major": (
            40,
            True,
            {
                "en": "Major",
                "ko": "전공",
                "zh-hans": "专业",
                "lo": "ສາຂາວິຊາ",
                "de": "Studienfach",
                "ru": "Специальность",
                "ms": "Major",
                "fil": "Major",
                "fr": "Spécialité",
                "ja": "専攻",
                "mn": "Мэргэжил",
                "ne": "मुख्य विषय",
                "th": "สาขาวิชา",
                "tr": "Ana dal",
                "uz": "Mutaxassislik",
                "vi": "Ngành",
            },
        ),
        "office": (
            90,
            False,
            {
                "en": "Administrative office",
                "ko": "행정 부서",
                "zh-hans": "行政部门",
                "lo": "ຫ້ອງການບໍລິຫານ",
                "de": "Verwaltungsstelle",
                "ru": "Административное подразделение",
                "ms": "Pejabat pentadbiran",
                "fil": "Opisinang administratibo",
                "fr": "Service administratif",
                "ja": "事務部署",
                "mn": "Захиргааны алба",
                "ne": "प्रशासनिक कार्यालय",
                "th": "หน่วยงานสนับสนุน",
                "tr": "İdari birim",
                "uz": "Maʼmuriy boʻlim",
                "vi": "Phòng ban hành chính",
            },
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
