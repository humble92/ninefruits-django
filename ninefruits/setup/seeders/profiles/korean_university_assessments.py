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
    (
        "LISTENING",
        {
            "en": "Listening",
            "ko": "듣기",
            "zh-hans": "听力",
            "lo": "ການຟັງ",
            "de": "Hörverstehen",
            "ru": "Аудирование",
            "ms": "Mendengar",
            "fil": "Pakikinig",
            "fr": "Compréhension orale",
            "ja": "リスニング",
            "mn": "Сонсох",
            "ne": "सुनाइ",
            "th": "การฟัง",
            "tr": "Dinleme",
            "uz": "Tinglab tushunish",
            "vi": "Nghe",
        },
    ),
    (
        "READING",
        {
            "en": "Reading",
            "ko": "읽기",
            "zh-hans": "阅读",
            "lo": "ການອ່ານ",
            "de": "Leseverstehen",
            "ru": "Чтение",
            "ms": "Membaca",
            "fil": "Pagbasa",
            "fr": "Compréhension écrite",
            "ja": "リーディング",
            "mn": "Унших",
            "ne": "पढाइ",
            "th": "การอ่าน",
            "tr": "Okuma",
            "uz": "Oʻqish",
            "vi": "Đọc",
        },
    ),
    (
        "WRITING",
        {
            "en": "Writing",
            "ko": "쓰기",
            "zh-hans": "写作",
            "lo": "ການຂຽນ",
            "de": "Schreiben",
            "ru": "Письмо",
            "ms": "Menulis",
            "fil": "Pagsulat",
            "fr": "Expression écrite",
            "ja": "ライティング",
            "mn": "Бичих",
            "ne": "लेखाइ",
            "th": "การเขียน",
            "tr": "Yazma",
            "uz": "Yozish",
            "vi": "Viết",
        },
    ),
    (
        "GRAMMAR",
        {
            "en": "Grammar",
            "ko": "문법",
            "zh-hans": "语法",
            "lo": "ໄວຍາກອນ",
            "de": "Grammatik",
            "ru": "Грамматика",
            "ms": "Tatabahasa",
            "fil": "Gramatika",
            "fr": "Grammaire",
            "ja": "文法",
            "mn": "Дүрэм",
            "ne": "व्याकरण",
            "th": "ไวยากรณ์",
            "tr": "Dil bilgisi",
            "uz": "Grammatika",
            "vi": "Ngữ pháp",
        },
    ),
]

KINDS: list[tuple[str, dict[str, str], dict[str, Any]]] = [
    (
        "ENG_COMP",
        {
            "en": "English comprehensive examination",
            "ko": "영어종합시험",
            "zh-hans": "英语综合考试",
            "lo": "ການສອບເສັງພາສາອັງກິດລວມ",
            "de": "Englisch-Gesamtprüfung",
            "ru": "Комплексный экзамен по английскому языку",
            "ms": "Peperiksaan komprehensif bahasa Inggeris",
            "fil": "Komprehensibong pagsusulit sa Ingles",
            "fr": "Examen général d’anglais",
            "ja": "英語総合試験",
            "mn": "Англи хэлний иж бүрэн шалгалт",
            "ne": "अङ्ग्रेजी व्यापक परीक्षा",
            "th": "การสอบประมวลความรู้ภาษาอังกฤษ",
            "tr": "İngilizce yeterlik sınavı",
            "uz": "Ingliz tili boʻyicha kompleks imtihon",
            "vi": "Kỳ thi tổng hợp tiếng Anh",
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
            "de": "Informatik-Gesamtprüfung",
            "ru": "Комплексный экзамен по информатике",
            "ms": "Peperiksaan komprehensif komputer",
            "fil": "Komprehensibong pagsusulit sa kompyuter",
            "fr": "Examen général d’informatique",
            "ja": "情報処理総合試験",
            "mn": "Компьютерийн иж бүрэн шалгалт",
            "ne": "कम्प्युटर व्यापक परीक्षा",
            "th": "การสอบประมวลความรู้คอมพิวเตอร์",
            "tr": "Bilgisayar yeterlik sınavı",
            "uz": "Kompyuter savodxonligi boʻyicha kompleks imtihon",
            "vi": "Kỳ thi tổng hợp tin học",
        },
        {"category": "comprehensive", "scoring": "pass_fail", "sort_order": 20},
    ),
    (
        "THESIS",
        {
            "en": "Graduation thesis",
            "ko": "졸업논문",
            "zh-hans": "毕业论文",
            "lo": "ບົດວິທະຍານິພົນຈົບການສຶກສາ",
            "de": "Abschlussarbeit",
            "ru": "Выпускная квалификационная работа",
            "ms": "Tesis tamat pengajian",
            "fil": "Tesis sa pagtatapos",
            "fr": "Mémoire de fin d’études",
            "ja": "卒業論文",
            "mn": "Дипломын ажил",
            "ne": "स्नातक शोधपत्र",
            "th": "วิทยานิพนธ์เพื่อสำเร็จการศึกษา",
            "tr": "Bitirme tezi",
            "uz": "Bitiruv malakaviy ishi",
            "vi": "Khóa luận tốt nghiệp",
        },
        {"category": "thesis", "scoring": "pass_fail", "sort_order": 30},
    ),
    (
        "TOPIK",
        {
            "en": "TOPIK (Test of Proficiency in Korean)",
            "ko": "한국어능력시험(TOPIK)",
            "zh-hans": "韩国语能力考试（TOPIK）",
            "lo": "ການສອບເສັງຄວາມສາມາດພາສາເກົາຫຼີ (TOPIK)",
            "de": "TOPIK (Koreanisch-Sprachtest)",
            "ru": "TOPIK (тест на знание корейского языка)",
            "ms": "TOPIK (Ujian Kecekapan Bahasa Korea)",
            "fil": "TOPIK (Test of Proficiency in Korean)",
            "fr": "TOPIK (test de compétence en coréen)",
            "ja": "韓国語能力試験(TOPIK)",
            "mn": "TOPIK (Солонгос хэлний түвшин тогтоох шалгалт)",
            "ne": "कोरियाली भाषा दक्षता परीक्षा (TOPIK)",
            "th": "การสอบวัดระดับความสามารถภาษาเกาหลี (TOPIK)",
            "tr": "TOPIK (Korece Yeterlik Sınavı)",
            "uz": "TOPIK (Koreys tilini bilish darajasi testi)",
            "vi": "TOPIK (Kỳ thi năng lực tiếng Hàn)",
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
