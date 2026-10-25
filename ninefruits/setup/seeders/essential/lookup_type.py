from __future__ import annotations

from ninefruits.institution.models import LookupType
from ninefruits.setup.seeders.base import Seeder, seed_row

#: Code list of admission types (Phase 3 ``Application.ADMISSION_TYPE_LOOKUP``).
ADMISSION_TYPE_LOOKUP = "admission_type"
#: Code list of application document types (Phase 3 ``Application.DOCUMENT_TYPE_LOOKUP``).
DOCUMENT_TYPE_LOOKUP = "application_document_type"
#: Code list of room types (``Room.ROOM_TYPE_LOOKUP``).
ROOM_TYPE_LOOKUP = "room_type"


class LookupTypeSeeder(Seeder):
    """Code lists the application refers to by code. Values are institution specific and come
    from profiles, CSV import or the admin panel."""

    SYSTEM_TYPES: dict[str, dict[str, str]] = {
        "ethnicity": {"en": "Ethnicity", "ko": "민족", "zh-hans": "民族", "lo": "ຊົນເຜົ່າ"},
        ADMISSION_TYPE_LOOKUP: {
            "en": "Admission type",
            "ko": "입학 구분",
            "zh-hans": "入学类别",
            "lo": "ປະເພດການຮັບເຂົ້າຮຽນ",
        },
        DOCUMENT_TYPE_LOOKUP: {
            "en": "Application document type",
            "ko": "지원 제출 서류",
            "zh-hans": "申请材料类型",
            "lo": "ປະເພດເອກະສານສະໝັກ",
        },
        ROOM_TYPE_LOOKUP: {"en": "Room type", "ko": "강의실 용도", "zh-hans": "教室用途", "lo": "ການນຳໃຊ້ຫ້ອງຮຽນ"},
    }

    def run(self) -> None:
        for code, name in self.SYSTEM_TYPES.items():
            lookup_type = seed_row(LookupType, {"code": code}, {"name": name})
            if not lookup_type.is_system:
                lookup_type.is_system = True
                lookup_type.save(update_fields=["is_system", "updated_at"])
