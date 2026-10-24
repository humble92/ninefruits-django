"""Phase 7 step of the ``korean-university`` profile (original
``KoreanUniversityProfileSeeder::evaluationForm``, ADR 0012): a standard course evaluation of five
areas with three questions each on a five-point scale (the legacy areas), one reversed, and one
comment. Created once; changes administrators make are kept."""

from __future__ import annotations

from typing import Any

Names = dict[str, str]

FORM: dict[str, Any] = {
    "code": "STANDARD",
    "name": {
        "en": "Standard course evaluation",
        "ko": "표준 강의평가",
        "zh-hans": "标准课程评价",
        "lo": "ການປະເມີນລາຍວິຊາມາດຕະຖານ",
    },
    "description": {
        "en": "Your answers are anonymous: instructors see only totals, after the results are published, and "
        "only when enough students answered.",
        "ko": "응답은 익명입니다. 교원은 결과 공개 후, 충분한 학생이 응답한 강좌의 집계만 봅니다.",
        "zh-hans": "回答为匿名。教师只能在结果公布后、回答人数足够时看到汇总结果。",
        "lo": "ຄຳຕອບຂອງທ່ານເປັນຄວາມລັບ: ອາຈານຈະເຫັນພຽງຜົນລວມຫຼັງຈາກປະກາດຜົນແລ້ວ ແລະ ສະເພາະເມື່ອມີນັກສຶກສາຕອບພຽງພໍເທົ່ານັ້ນ.",
    },
    "scale_points": 5,
    "scale_low_label": {
        "en": "Strongly disagree",
        "ko": "전혀 그렇지 않다",
        "zh-hans": "完全不同意",
        "lo": "ບໍ່ເຫັນດີຢ່າງຍິ່ງ",
    },
    "scale_high_label": {"en": "Strongly agree", "ko": "매우 그렇다", "zh-hans": "非常同意", "lo": "ເຫັນດີຢ່າງຍິ່ງ"},
}

#: (area, [(question, reversed)])
AREAS: list[tuple[Names, list[tuple[Names, bool]]]] = [
    (
        {"en": "Preparation", "ko": "강의 준비", "zh-hans": "课程准备", "lo": "ການກະກຽມການສອນ"},
        [
            (
                {
                    "en": "The syllabus explained the goals, content and grading of the course.",
                    "ko": "강의계획서에 수업 목표, 내용, 평가 방법이 잘 안내되었다.",
                    "zh-hans": "教学大纲清楚说明了课程目标、内容和评分方法。",
                    "lo": "ຫຼັກສູດການສອນໄດ້ອະທິບາຍເປົ້າໝາຍ, ເນື້ອໃນ ແລະ ວິທີການໃຫ້ຄະແນນຂອງລາຍວິຊາຢ່າງຈະແຈ້ງ.",
                },
                False,
            ),
            (
                {
                    "en": "Classes were well prepared.",
                    "ko": "수업이 충실히 준비되었다.",
                    "zh-hans": "课程准备充分。",
                    "lo": "ການສອນໄດ້ກະກຽມມາເປັນຢ່າງດີ.",
                },
                False,
            ),
            (
                {
                    "en": "Classes started and ended on time.",
                    "ko": "수업이 정해진 시간에 시작하고 끝났다.",
                    "zh-hans": "课程按时开始和结束。",
                    "lo": "ການສອນເລີ່ມ ແລະ ສິ້ນສຸດຕາມເວລາທີ່ກຳນົດ.",
                },
                False,
            ),
        ],
    ),
    (
        {"en": "Teaching", "ko": "강의 방법", "zh-hans": "教学方法", "lo": "ວິທີການສອນ"},
        [
            (
                {
                    "en": "Explanations were clear and easy to follow.",
                    "ko": "설명이 명확하고 이해하기 쉬웠다.",
                    "zh-hans": "讲解清楚易懂。",
                    "lo": "ການອະທິບາຍຈະແຈ້ງ ແລະ ເຂົ້າໃຈງ່າຍ.",
                },
                False,
            ),
            (
                {
                    "en": "Students could ask questions and take part.",
                    "ko": "질문과 참여의 기회가 충분했다.",
                    "zh-hans": "学生有充分的提问和参与机会。",
                    "lo": "ນັກສຶກສາມີໂອກາດຖາມ ແລະ ມີສ່ວນຮ່ວມຢ່າງພຽງພໍ.",
                },
                False,
            ),
            (
                {
                    "en": "The pace of the course was hard to follow.",
                    "ko": "수업 진도를 따라가기 어려웠다.",
                    "zh-hans": "课程进度很难跟上。",
                    "lo": "ຈັງຫວະການສອນຕິດຕາມໄດ້ຍາກ.",
                },
                True,
            ),
        ],
    ),
    (
        {"en": "Content", "ko": "강의 내용", "zh-hans": "教学内容", "lo": "ເນື້ອໃນການສອນ"},
        [
            (
                {
                    "en": "The content followed the syllabus.",
                    "ko": "수업 내용이 강의계획서에 맞게 진행되었다.",
                    "zh-hans": "教学内容与教学大纲一致。",
                    "lo": "ເນື້ອໃນການສອນສອດຄ່ອງກັບຫຼັກສູດການສອນ.",
                },
                False,
            ),
            (
                {
                    "en": "The course increased my knowledge of the subject.",
                    "ko": "이 과목에 대한 지식이 늘었다.",
                    "zh-hans": "这门课增加了我对该学科的了解。",
                    "lo": "ລາຍວິຊານີ້ເຮັດໃຫ້ຂ້ອຍມີຄວາມຮູ້ໃນວິຊານີ້ເພີ່ມຂຶ້ນ.",
                },
                False,
            ),
            (
                {
                    "en": "Materials and assignments helped me learn.",
                    "ko": "교재와 과제가 학습에 도움이 되었다.",
                    "zh-hans": "教材和作业对学习有帮助。",
                    "lo": "ເອກະສານການສອນ ແລະ ວຽກບ້ານຊ່ວຍໃນການຮຽນຮູ້.",
                },
                False,
            ),
        ],
    ),
    (
        {"en": "Assessment", "ko": "평가 방법", "zh-hans": "考核方法", "lo": "ວິທີການປະເມີນຜົນ"},
        [
            (
                {
                    "en": "Assessment followed the announced criteria.",
                    "ko": "평가가 안내된 기준에 따라 이루어졌다.",
                    "zh-hans": "考核按照公布的标准进行。",
                    "lo": "ການປະເມີນຜົນເປັນໄປຕາມເກນທີ່ປະກາດໄວ້.",
                },
                False,
            ),
            (
                {
                    "en": "Exams and assignments matched what was taught.",
                    "ko": "시험과 과제가 수업 내용과 맞았다.",
                    "zh-hans": "考试和作业与教学内容相符。",
                    "lo": "ການສອບເສັງ ແລະ ວຽກບ້ານສອດຄ່ອງກັບເນື້ອໃນທີ່ສອນ.",
                },
                False,
            ),
            (
                {
                    "en": "I received useful feedback on my work.",
                    "ko": "과제와 시험에 대해 도움이 되는 피드백을 받았다.",
                    "zh-hans": "我得到了对学习有帮助的反馈。",
                    "lo": "ຂ້ອຍໄດ້ຮັບຄຳຕິຊົມທີ່ເປັນປະໂຫຍດຕໍ່ວຽກຂອງຂ້ອຍ.",
                },
                False,
            ),
        ],
    ),
    (
        {
            "en": "Facilities",
            "ko": "교학 시설 및 장비",
            "zh-hans": "教学设施和设备",
            "lo": "ສິ່ງອຳນວຍຄວາມສະດວກ ແລະ ອຸປະກອນການສອນ",
        },
        [
            (
                {
                    "en": "The classroom was suitable for the course.",
                    "ko": "강의실이 수업에 적합했다.",
                    "zh-hans": "教室适合本课程。",
                    "lo": "ຫ້ອງຮຽນເໝາະສົມກັບລາຍວິຊາ.",
                },
                False,
            ),
            (
                {
                    "en": "Equipment needed for the course worked well.",
                    "ko": "수업에 필요한 장비가 잘 작동했다.",
                    "zh-hans": "课程所需设备运行良好。",
                    "lo": "ອຸປະກອນທີ່ຈຳເປັນສຳລັບລາຍວິຊາໃຊ້ງານໄດ້ດີ.",
                },
                False,
            ),
            (
                {
                    "en": "Overall, I am satisfied with this course.",
                    "ko": "전반적으로 이 수업에 만족한다.",
                    "zh-hans": "总体上我对这门课感到满意。",
                    "lo": "ໂດຍລວມແລ້ວ ຂ້ອຍພໍໃຈກັບລາຍວິຊານີ້.",
                },
                False,
            ),
        ],
    ),
]

COMMENT_AREA: Names = {"en": "Comments", "ko": "의견", "zh-hans": "意见", "lo": "ຄຳຄິດເຫັນ"}
COMMENT: Names = {
    "en": "What should the instructor keep or change?",
    "ko": "이 수업에서 좋았던 점이나 바뀌었으면 하는 점을 적어 주세요.",
    "zh-hans": "请写下这门课的优点或需要改进的地方。",
    "lo": "ກະລຸນາຂຽນສິ່ງທີ່ດີຂອງລາຍວິຊານີ້ ຫຼື ສິ່ງທີ່ຢາກໃຫ້ປ່ຽນແປງ.",
}


def seed_evaluation_form(profile: Any = None) -> Any:
    """``LATER_PHASE_STEPS`` entry of ``KoreanUniversityProfileSeeder``. Returns the form."""
    from ninefruits.evaluation.enums import QuestionType
    from ninefruits.evaluation.models import EvaluationForm, EvaluationQuestion

    existing = EvaluationForm.objects.filter(code=FORM["code"]).first()
    if existing is not None:
        return existing
    form = EvaluationForm.objects.create(**FORM)
    questions = []
    order = 0
    for category, texts in AREAS:
        for text, reversed_ in texts:
            order += 10
            questions.append(
                EvaluationQuestion(form=form, sort_order=order, category=category, text=text, is_reversed=reversed_)
            )
    questions.append(
        EvaluationQuestion(
            form=form,
            sort_order=order + 10,
            category=COMMENT_AREA,
            text=COMMENT,
            question_type=QuestionType.TEXT,
            is_required=False,
        )
    )
    EvaluationQuestion.objects.bulk_create(questions)
    return form
