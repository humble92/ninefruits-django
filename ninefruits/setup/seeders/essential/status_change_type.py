from __future__ import annotations

from ninefruits.person.enums import StudentStatus
from ninefruits.person.models import StudentStatusChangeType
from ninefruits.setup.seeders.base import Seeder, seed_row

_ENROLLED = StudentStatus.ENROLLED.value
_ON_LEAVE = StudentStatus.ON_LEAVE.value


class StatusChangeTypeSeeder(Seeder):
    """System status change kinds (legacy SRALTERDEF). The transition (from statuses -> status)
    of system kinds is fixed; names and whether students may request them are editable."""

    #: code -> (to, from, students may request, order, name)
    TYPES: dict[str, tuple[StudentStatus, list[str], bool, int, dict[str, str]]] = {
        "leave_of_absence": (
            StudentStatus.ON_LEAVE,
            [_ENROLLED],
            True,
            10,
            {
                "en": "Leave of absence",
                "ko": "휴학",
                "zh-hans": "休学",
                "lo": "ການພັກການຮຽນ",
                "de": "Beurlaubung",
                "ru": "Академический отпуск",
                "ms": "Penangguhan pengajian",
                "fil": "Leave of absence",
                "fr": "Congé",
                "ja": "休学",
                "mn": "Чөлөө",
                "ne": "अध्ययन बिदा",
                "th": "ลาพักการศึกษา",
                "tr": "Kayıt dondurma",
                "uz": "Akademik taʼtil",
                "vi": "Bảo lưu",
            },
        ),
        "return_from_leave": (
            StudentStatus.ENROLLED,
            [_ON_LEAVE],
            True,
            20,
            {
                "en": "Return from leave",
                "ko": "복학",
                "zh-hans": "复学",
                "lo": "ການກັບຄືນມາຮຽນ",
                "de": "Rückkehr aus der Beurlaubung",
                "ru": "Выход из академического отпуска",
                "ms": "Sambung semula pengajian",
                "fil": "Pagbalik mula sa leave",
                "fr": "Reprise d’études",
                "ja": "復学",
                "mn": "Чөлөөнөөс эргэн орох",
                "ne": "अध्ययनमा पुनरागमन",
                "th": "กลับเข้าศึกษา",
                "tr": "Kayıt dondurma sonrası dönüş",
                "uz": "Akademik taʼtildan qaytish",
                "vi": "Trở lại học",
            },
        ),
        "withdrawal": (
            StudentStatus.WITHDRAWN,
            [_ENROLLED, _ON_LEAVE],
            True,
            30,
            {
                "en": "Withdrawal",
                "ko": "자퇴",
                "zh-hans": "退学",
                "lo": "ການອອກຈາກການຮຽນ",
                "de": "Exmatrikulation auf Antrag",
                "ru": "Отчисление по собственному желанию",
                "ms": "Tarik diri",
                "fil": "Pag-withdraw",
                "fr": "Abandon",
                "ja": "退学",
                "mn": "Сургуулиас гарах",
                "ne": "अध्ययन परित्याग",
                "th": "ลาออก",
                "tr": "Kendi isteğiyle ayrılma",
                "uz": "Oʻqishdan chiqish",
                "vi": "Thôi học",
            },
        ),
        "dismissal": (
            StudentStatus.DISMISSED,
            [_ENROLLED, _ON_LEAVE],
            False,
            40,
            {
                "en": "Dismissal",
                "ko": "제적",
                "zh-hans": "开除学籍",
                "lo": "ການໄລ່ອອກຈາກການຮຽນ",
                "de": "Exmatrikulation von Amts wegen",
                "ru": "Отчисление",
                "ms": "Pemberhentian",
                "fil": "Pagkatanggal",
                "fr": "Exclusion",
                "ja": "除籍",
                "mn": "Сургуулиас хасах",
                "ne": "निष्कासन",
                "th": "พ้นสภาพ",
                "tr": "İlişik kesme",
                "uz": "Oʻqishdan chetlashtirish",
                "vi": "Buộc thôi học",
            },
        ),
        "readmission": (
            StudentStatus.ENROLLED,
            [StudentStatus.WITHDRAWN.value, StudentStatus.DISMISSED.value],
            False,
            50,
            {
                "en": "Readmission",
                "ko": "재입학",
                "zh-hans": "重新入学",
                "lo": "ການຮັບເຂົ້າຮຽນຄືນ",
                "de": "Wiedereinschreibung",
                "ru": "Восстановление",
                "ms": "Kemasukan semula",
                "fil": "Muling pagtanggap",
                "fr": "Réadmission",
                "ja": "再入学",
                "mn": "Дахин элсэх",
                "ne": "पुनर्भर्ना",
                "th": "คืนสภาพนักศึกษา",
                "tr": "Yeniden kayıt",
                "uz": "Oʻqishga qayta tiklash",
                "vi": "Tiếp nhận học lại",
            },
        ),
        "graduation": (
            StudentStatus.GRADUATED,
            [_ENROLLED],
            False,
            60,
            {
                "en": "Graduation",
                "ko": "졸업",
                "zh-hans": "毕业",
                "lo": "ການຈົບການສຶກສາ",
                "de": "Studienabschluss",
                "ru": "Выпуск",
                "ms": "Bergraduat",
                "fil": "Pagtatapos",
                "fr": "Obtention du diplôme",
                "ja": "卒業",
                "mn": "Төгсөлт",
                "ne": "स्नातक",
                "th": "สำเร็จการศึกษา",
                "tr": "Mezuniyet",
                "uz": "Bitirish",
                "vi": "Tốt nghiệp",
            },
        ),
    }

    def run(self) -> None:
        for code, (to_status, from_statuses, can_request, order, name) in self.TYPES.items():
            change_type = seed_row(
                StudentStatusChangeType,
                {"code": code},
                {"name": name},
                {
                    "to_status": to_status,
                    "from_statuses": from_statuses,
                    "can_student_request": can_request,
                    "sort_order": order,
                },
            )
            change_type.is_system = True
            change_type.to_status = to_status
            change_type.from_statuses = from_statuses
            change_type.save(update_fields=["is_system", "to_status", "from_statuses", "updated_at"])
