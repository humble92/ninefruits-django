"""Certificate part of the ``korean-university`` profile (original
``KoreanUniversityProfileSeeder::certificateTypes``, Phase 8): the kinds the legacy issued
(재학, 졸업, 성적증명서) with their wording in Korean, English, Simplified Chinese and Lao.

Created once: when any kind exists, nothing is added, so the institution's edits to the kinds
and templates stay (ADR 0013)."""

from __future__ import annotations

from typing import Any

#: The footer of every template, by language.
FOOTERS: dict[str, str] = {
    "ko": "이 증명서의 진위는 아래 QR 코드 또는 확인 주소에서 확인할 수 있습니다.",
    "en": "Verify this certificate with the QR code or at the address below.",
    "zh-hans": "可通过下方二维码或网址核验本证明。",
    "lo": "ສາມາດກວດສອບຄວາມຖືກຕ້ອງຂອງໃບຢັ້ງຢືນນີ້ ດ້ວຍລະຫັດ QR ຫຼື ທີ່ຢູ່ຂ້າງລຸ່ມນີ້.",
}

#: (code, name, audience, includes grades, {language: (title, body, signer)})
KINDS: list[tuple[str, dict[str, str], str, bool, dict[str, tuple[str, str, str]]]] = [
    (
        "ENR",
        {"en": "Certificate of Enrollment", "ko": "재학증명서", "zh-hans": "在学证明书", "lo": "ໃບຢັ້ງຢືນການເປັນນັກສຶກສາ"},
        "enrolled",
        False,
        {
            "ko": ("재학증명서", "위의 사람이 본교에 재학 중임을 증명합니다.\n\n용도: {purpose}", "교무처장"),
            "en": (
                "Certificate of Enrollment",
                "This is to certify that the above mentioned is presently enrolled at {institution}.\n\n"
                "Purpose: {purpose}",
                "Dean of Academic Affairs",
            ),
            "zh-hans": ("在学证明书", "兹证明上述学生现在本校在读。\n\n用途：{purpose}", "教务处长"),
            "lo": (
                "ໃບຢັ້ງຢືນການເປັນນັກສຶກສາ",
                "ຂໍຢັ້ງຢືນວ່າ ບຸກຄົນທີ່ມີຊື່ຂ້າງເທິງນີ້ ກຳລັງສຶກສາຢູ່ {institution}.\n\nຈຸດປະສົງ: {purpose}",
                "ຫົວໜ້າຫ້ອງການວິຊາການ",
            ),
        },
    ),
    (
        "GRD",
        {"en": "Certificate of Graduation", "ko": "졸업증명서", "zh-hans": "毕业证明书", "lo": "ໃບຢັ້ງຢືນການຈົບການສຶກສາ"},
        "graduated",
        False,
        {
            "ko": (
                "졸업증명서",
                "위의 사람이 {graduation_date} 본교 {program}을(를) 졸업하였음을 증명합니다.\n\n"
                "학위번호: {degree_number}",
                "교무처장",
            ),
            "en": (
                "Certificate of Graduation",
                "This is to certify that the above mentioned graduated from {institution}, {program}, on "
                "{graduation_date}.\n\nDiploma no.: {degree_number}",
                "Dean of Academic Affairs",
            ),
            "zh-hans": (
                "毕业证明书",
                "兹证明上述学生于{graduation_date}在本校{program}毕业。\n\n学位证书编号：{degree_number}",
                "教务处长",
            ),
            "lo": (
                "ໃບຢັ້ງຢືນການຈົບການສຶກສາ",
                "ຂໍຢັ້ງຢືນວ່າ ບຸກຄົນທີ່ມີຊື່ຂ້າງເທິງນີ້ ໄດ້ຈົບການສຶກສາຈາກ {institution} ຫຼັກສູດ {program} ໃນວັນທີ "
                "{graduation_date}.\n\nເລກທີໃບປະກາດ: {degree_number}",
                "ຫົວໜ້າຫ້ອງການວິຊາການ",
            ),
        },
    ),
    (
        "TRN",
        {"en": "Academic Transcript", "ko": "성적증명서", "zh-hans": "成绩证明书", "lo": "ໃບຢັ້ງຢືນຜົນການຮຽນ"},
        "any",
        True,
        {
            "ko": ("성적증명서", "위의 사람의 성적이 아래와 같음을 증명합니다.", "교무처장"),
            "en": (
                "Academic Transcript",
                "I certify that the transcript below is a complete and authentic copy of the academic record of the "
                "above mentioned.",
                "Dean of Academic Affairs",
            ),
            "zh-hans": ("成绩证明书", "兹证明上述学生的成绩如下。", "教务处长"),
            "lo": (
                "ໃບຢັ້ງຢືນຜົນການຮຽນ",
                "ຂໍຢັ້ງຢືນວ່າ ຜົນການຮຽນຂ້າງລຸ່ມນີ້ ແມ່ນສຳເນົາທີ່ຄົບຖ້ວນ ແລະ ຖືກຕ້ອງຂອງບັນທຶກການສຶກສາຂອງບຸກຄົນທີ່ມີຊື່ຂ້າງເທິງ.",
                "ຫົວໜ້າຫ້ອງການວິຊາການ",
            ),
        },
    ),
]


def seed_certificate_types(profile: Any = None) -> None:
    """``LATER_PHASE_STEPS`` entry of ``KoreanUniversityProfileSeeder``."""
    from ninefruits.certificate.models import CertificateTemplate, CertificateType

    if CertificateType.objects.exists():
        return
    order = 0
    for code, name, audience, has_grades, templates in KINDS:
        order += 10
        kind = CertificateType.objects.create(
            code=code, name=name, audience=audience, has_grades=has_grades, sort_order=order
        )
        CertificateTemplate.objects.bulk_create(
            CertificateTemplate(
                certificate_type=kind, locale=locale, title=title, body=body, signer=signer, footer=FOOTERS[locale]
            )
            for locale, (title, body, signer) in templates.items()
        )
