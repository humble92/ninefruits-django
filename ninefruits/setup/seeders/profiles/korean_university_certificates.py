# ruff: noqa: E501
"""Certificate part of the ``korean-university`` profile (original
``KoreanUniversityProfileSeeder::certificateTypes``, Phase 8): the kinds the legacy issued
(재학, 졸업, 성적증명서) with their wording in every shipped language
(Korean, English, Simplified Chinese, Lao and the twelve languages added on 2026-11-11).

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
    "de": "Prüfen Sie die Echtheit dieser Bescheinigung über den QR-Code oder unter der folgenden Adresse.",
    "ru": "Подлинность справки можно проверить по QR-коду или по адресу ниже.",
    "ms": "Sahkan sijil ini melalui kod QR atau di alamat di bawah.",
    "fil": "I-verify ang sertipikong ito gamit ang QR code o sa address sa ibaba.",
    "fr": "Vérifiez cette attestation avec le code QR ou à l’adresse ci-dessous.",
    "ja": "この証明書の真正性は、QR コードまたは下記のアドレスで確認できます。",
    "mn": "Энэ тодорхойлолтыг QR кодоор эсвэл доорх хаягаар баталгаажуулна уу.",
    "ne": "यो प्रमाणपत्र QR कोडबाट वा तलको ठेगानामा प्रमाणित गर्नुहोस्।",
    "th": "ตรวจสอบความถูกต้องของหนังสือรับรองนี้ได้ด้วย QR code หรือที่อยู่ด้านล่าง",
    "tr": "Bu belgeyi QR kodu ile veya aşağıdaki adresten doğrulayabilirsiniz.",
    "uz": "Ushbu maʼlumotnomaning haqiqiyligini QR kod orqali yoki quyidagi manzilda tekshiring.",
    "vi": "Xác minh giấy chứng nhận này bằng mã QR hoặc tại địa chỉ dưới đây.",
}

#: (code, name, audience, includes grades, {language: (title, body, signer)})
KINDS: list[tuple[str, dict[str, str], str, bool, dict[str, tuple[str, str, str]]]] = [
    (
        "ENR",
        {
            "en": "Certificate of Enrollment",
            "ko": "재학증명서",
            "zh-hans": "在学证明书",
            "lo": "ໃບຢັ້ງຢືນການເປັນນັກສຶກສາ",
            "de": "Immatrikulationsbescheinigung",
            "ru": "Справка об обучении",
            "ms": "Surat Pengesahan Pelajar",
            "fil": "Certificate of Enrollment",
            "fr": "Certificat de scolarité",
            "ja": "在学証明書",
            "mn": "Суралцаж буйг гэрчлэх тодорхойлолт",
            "ne": "अध्ययनरत प्रमाणपत्र",
            "th": "หนังสือรับรองการเป็นนักศึกษา",
            "tr": "Öğrenci Belgesi",
            "uz": "Talabalik haqida maʼlumotnoma",
            "vi": "Giấy xác nhận sinh viên",
        },
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
            "de": (
                "Immatrikulationsbescheinigung",
                "Hiermit wird bescheinigt, dass die oben genannte Person derzeit an der {institution} immatrikuliert ist.\n\nVerwendungszweck: {purpose}",
                "Vizepräsident/in für Studium und Lehre",
            ),
            "ru": (
                "Справка об обучении",
                "Настоящая справка подтверждает, что указанное выше лицо в настоящее время обучается в {institution}.\n\nСправка выдана для представления: {purpose}",
                "Проректор по учебной работе",
            ),
            "ms": (
                "Surat Pengesahan Pelajar",
                "Adalah disahkan bahawa individu yang tersebut di atas kini sedang mengikuti pengajian di {institution}.\n\nTujuan: {purpose}",
                "Dekan Hal Ehwal Akademik",
            ),
            "fil": (
                "Certificate of Enrollment",
                "Ito ay nagpapatunay na ang nabanggit sa itaas ay kasalukuyang naka-enroll sa {institution}.\n\nLayunin: {purpose}",
                "Dekano ng Academic Affairs",
            ),
            "fr": (
                "Certificat de scolarité",
                "Nous certifions que la personne susmentionnée est actuellement inscrite à {institution}.\n\nObjet : {purpose}",
                "Le Vice-président chargé des formations",
            ),
            "ja": (
                "在学証明書",
                "上記の者は、現在 {institution} に在学していることを証明します。\n\n用途: {purpose}",
                "教務部長",
            ),
            "mn": (
                "Суралцаж буйг гэрчлэх тодорхойлолт",
                "Дээр дурдсан хүн {institution}-д одоо суралцаж байгааг тодорхойлов.\n\nЗориулалт: {purpose}",
                "Сургалт хариуцсан дэд захирал",
            ),
            "ne": (
                "अध्ययनरत प्रमाणपत्र",
                "माथि उल्लिखित व्यक्ति हाल {institution} मा अध्ययनरत हुनुहुन्छ भनी प्रमाणित गरिन्छ।\n\nप्रयोजन: {purpose}",
                "शैक्षिक प्रशासन प्रमुख",
            ),
            "th": (
                "หนังสือรับรองการเป็นนักศึกษา",
                "หนังสือฉบับนี้ให้ไว้เพื่อรับรองว่าผู้มีรายนามข้างต้นเป็นนักศึกษาของ {institution} ในปัจจุบัน\n\nวัตถุประสงค์: {purpose}",
                "รองอธิการบดีฝ่ายวิชาการ",
            ),
            "tr": (
                "Öğrenci Belgesi",
                "Yukarıda bilgileri yer alan kişinin {institution} öğrencisi olduğu onaylanır.\n\nKullanım amacı: {purpose}",
                "Öğrenci İşleri Daire Başkanı",
            ),
            "uz": (
                "Talabalik haqida maʼlumotnoma",
                "Ushbu maʼlumotnoma yuqorida koʻrsatilgan shaxs hozirda {institution}da tahsil olayotganini tasdiqlaydi.\n\nMaqsad: {purpose}",
                "Oʻquv ishlari boʻyicha prorektor",
            ),
            "vi": (
                "Giấy xác nhận sinh viên",
                "Xác nhận người có tên trên hiện đang là sinh viên của {institution}.\n\nMục đích: {purpose}",
                "Trưởng phòng Đào tạo",
            ),
        },
    ),
    (
        "GRD",
        {
            "en": "Certificate of Graduation",
            "ko": "졸업증명서",
            "zh-hans": "毕业证明书",
            "lo": "ໃບຢັ້ງຢືນການຈົບການສຶກສາ",
            "de": "Abschlussbescheinigung",
            "ru": "Справка об окончании",
            "ms": "Surat Pengesahan Tamat Pengajian",
            "fil": "Certificate of Graduation",
            "fr": "Attestation de réussite au diplôme",
            "ja": "卒業証明書",
            "mn": "Төгссөн тухай тодорхойлолт",
            "ne": "स्नातक प्रमाणपत्र",
            "th": "หนังสือรับรองการสำเร็จการศึกษา",
            "tr": "Mezuniyet Belgesi",
            "uz": "Bitirganlik haqida maʼlumotnoma",
            "vi": "Giấy chứng nhận tốt nghiệp",
        },
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
            "de": (
                "Abschlussbescheinigung",
                "Hiermit wird bescheinigt, dass die oben genannte Person am {graduation_date} den Studiengang {program} an der {institution} abgeschlossen hat.\n\nUrkundennummer: {degree_number}",
                "Vizepräsident/in für Studium und Lehre",
            ),
            "ru": (
                "Справка об окончании",
                "Настоящая справка подтверждает, что указанное выше лицо окончило {institution}, программа {program}, {graduation_date}.\n\nНомер диплома: {degree_number}",
                "Проректор по учебной работе",
            ),
            "ms": (
                "Surat Pengesahan Tamat Pengajian",
                "Adalah disahkan bahawa individu yang tersebut di atas telah bergraduat daripada {institution}, {program}, pada {graduation_date}.\n\nNo. ijazah: {degree_number}",
                "Dekan Hal Ehwal Akademik",
            ),
            "fil": (
                "Certificate of Graduation",
                "Ito ay nagpapatunay na ang nabanggit sa itaas ay nagtapos sa {institution}, {program}, noong {graduation_date}.\n\nBlg. ng diploma: {degree_number}",
                "Dekano ng Academic Affairs",
            ),
            "fr": (
                "Attestation de réussite au diplôme",
                "Nous certifions que la personne susmentionnée a obtenu son diplôme de {institution}, {program}, le {graduation_date}.\n\nN° de diplôme : {degree_number}",
                "Le Vice-président chargé des formations",
            ),
            "ja": (
                "卒業証明書",
                "上記の者は、{graduation_date} に {institution} {program} を卒業したことを証明します。\n\n学位記番号: {degree_number}",
                "教務部長",
            ),
            "mn": (
                "Төгссөн тухай тодорхойлолт",
                "Дээр дурдсан хүн {graduation_date}-нд {institution}-ийн {program} хөтөлбөрийг төгссөнийг тодорхойлов.\n\nДипломын дугаар: {degree_number}",
                "Сургалт хариуцсан дэд захирал",
            ),
            "ne": (
                "स्नातक प्रमाणपत्र",
                "माथि उल्लिखित व्यक्तिले {graduation_date} मा {institution}, {program} बाट स्नातक गर्नुभएको हो भनी प्रमाणित गरिन्छ।\n\nउपाधि नं.: {degree_number}",
                "शैक्षिक प्रशासन प्रमुख",
            ),
            "th": (
                "หนังสือรับรองการสำเร็จการศึกษา",
                "หนังสือฉบับนี้ให้ไว้เพื่อรับรองว่าผู้มีรายนามข้างต้นสำเร็จการศึกษาจาก {institution} หลักสูตร {program} เมื่อวันที่ {graduation_date}\n\nเลขที่ปริญญาบัตร: {degree_number}",
                "รองอธิการบดีฝ่ายวิชาการ",
            ),
            "tr": (
                "Mezuniyet Belgesi",
                "Yukarıda bilgileri yer alan kişinin {graduation_date} tarihinde {institution}, {program} programından mezun olduğu onaylanır.\n\nDiploma no.: {degree_number}",
                "Öğrenci İşleri Daire Başkanı",
            ),
            "uz": (
                "Bitirganlik haqida maʼlumotnoma",
                "Ushbu maʼlumotnoma yuqorida koʻrsatilgan shaxs {graduation_date} da {institution}, {program} dasturini bitirganini tasdiqlaydi.\n\nDiplom raqami: {degree_number}",
                "Oʻquv ishlari boʻyicha prorektor",
            ),
            "vi": (
                "Giấy chứng nhận tốt nghiệp",
                "Chứng nhận người có tên trên đã tốt nghiệp {institution}, {program}, ngày {graduation_date}.\n\nSố hiệu văn bằng: {degree_number}",
                "Trưởng phòng Đào tạo",
            ),
        },
    ),
    (
        "TRN",
        {
            "en": "Academic Transcript",
            "ko": "성적증명서",
            "zh-hans": "成绩证明书",
            "lo": "ໃບຢັ້ງຢືນຜົນການຮຽນ",
            "de": "Notenspiegel",
            "ru": "Академическая справка",
            "ms": "Transkrip Akademik",
            "fil": "Transcript of Records",
            "fr": "Relevé de notes",
            "ja": "成績証明書",
            "mn": "Дүнгийн хуудас",
            "ne": "शैक्षिक ट्रान्सक्रिप्ट",
            "th": "ใบแสดงผลการเรียน",
            "tr": "Transkript",
            "uz": "Akademik maʼlumotnoma",
            "vi": "Bảng điểm học tập",
        },
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
            "de": (
                "Notenspiegel",
                "Hiermit wird bescheinigt, dass der folgende Notenspiegel eine vollständige und echte Wiedergabe der Studienleistungen der oben genannten Person ist.",
                "Vizepräsident/in für Studium und Lehre",
            ),
            "ru": (
                "Академическая справка",
                "Удостоверяю, что приведённая ниже академическая справка является полной и достоверной копией сведений об успеваемости указанного выше лица.",
                "Проректор по учебной работе",
            ),
            "ms": (
                "Transkrip Akademik",
                "Saya mengesahkan bahawa transkrip di bawah ialah salinan lengkap dan sahih rekod akademik individu yang tersebut di atas.",
                "Dekan Hal Ehwal Akademik",
            ),
            "fil": (
                "Transcript of Records",
                "Pinatutunayan ko na ang transcript sa ibaba ay kumpleto at tunay na kopya ng akademikong rekord ng nabanggit sa itaas.",
                "Dekano ng Academic Affairs",
            ),
            "fr": (
                "Relevé de notes",
                "Je certifie que le relevé ci-dessous est une copie complète et authentique du dossier académique de la personne susmentionnée.",
                "Le Vice-président chargé des formations",
            ),
            "ja": (
                "成績証明書",
                "以下の成績は、上記の者の学業記録の完全かつ正確な写しであることを証明します。",
                "教務部長",
            ),
            "mn": (
                "Дүнгийн хуудас",
                "Доорх дүнгийн хуудас нь дээр дурдсан хүний сурлагын бүртгэлийн бүрэн, үнэн зөв хуулбар болохыг баталж байна.",
                "Сургалт хариуцсан дэд захирал",
            ),
            "ne": (
                "शैक्षिक ट्रान्सक्रिप्ट",
                "तलको ट्रान्सक्रिप्ट माथि उल्लिखित व्यक्तिको शैक्षिक अभिलेखको पूर्ण र प्रामाणिक प्रतिलिपि हो भनी म प्रमाणित गर्छु।",
                "शैक्षिक प्रशासन प्रमुख",
            ),
            "th": (
                "ใบแสดงผลการเรียน",
                "ขอรับรองว่าใบแสดงผลการเรียนด้านล่างนี้เป็นสำเนาที่ครบถ้วนและถูกต้องตรงตามระเบียนผลการเรียนของผู้มีรายนามข้างต้น",
                "รองอธิการบดีฝ่ายวิชาการ",
            ),
            "tr": (
                "Transkript",
                "Aşağıdaki transkriptin, yukarıda bilgileri yer alan kişinin akademik kaydının eksiksiz ve aslına uygun bir örneği olduğunu onaylarım.",
                "Öğrenci İşleri Daire Başkanı",
            ),
            "uz": (
                "Akademik maʼlumotnoma",
                "Quyidagi akademik maʼlumotnoma yuqorida koʻrsatilgan shaxsning oʻquv natijalari toʻgʻrisidagi toʻliq va haqiqiy nusxa ekanini tasdiqlayman.",
                "Oʻquv ishlari boʻyicha prorektor",
            ),
            "vi": (
                "Bảng điểm học tập",
                "Xác nhận bảng điểm dưới đây là bản đầy đủ và xác thực của kết quả học tập của người có tên trên.",
                "Trưởng phòng Đào tạo",
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
