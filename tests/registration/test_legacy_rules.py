"""Phase 5 completion criterion (original ``tests/Feature/Registration/LegacyRulesTest.php``): the
legacy YUST registration rules are reproduced by configuration alone (profile ``yust-legacy`` and
data), without the legacy bug of plan section 3.4 (nursing students from 2014 limited to 18
instead of 21)."""

from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal
from typing import Any

import pytest
from django.utils import timezone

from ninefruits.core.targeting import TargetCriteria
from ninefruits.curriculum.enums import RequisiteKind
from ninefruits.curriculum.models import CourseRequisite
from ninefruits.offering.actions import SaveSectionMeeting
from ninefruits.registration.actions import EnrollStudent, ManageHolds
from ninefruits.registration.enums import AttemptOutcome, HoldType, RuleCode
from ninefruits.registration.models import CreditLimitPolicy
from ninefruits.security.enums import Permission
from ninefruits.setup.seeders.profiles.yust_legacy import YustLegacyProfileSeeder
from ninefruits.term.enums import TermWindowType
from ninefruits.term.models import TermType
from tests.factories.curriculum import CourseFactory
from tests.factories.facility import RoomFactory
from tests.factories.offering import SectionFactory
from tests.factories.organization import OrgUnitFactory, ProgramFactory
from tests.factories.person import StudentRecordFactory
from tests.factories.registration import EnrollmentFactory
from tests.factories.security import UserFactory
from tests.factories.term import TermFactory

from .conftest import open_window

pytestmark = [pytest.mark.django_db, pytest.mark.usefixtures("essential_data")]


@pytest.fixture
def legacy(essential_data: None) -> dict[str, Any]:
    nursing_unit = OrgUnitFactory(code="NURS")
    other_unit = OrgUnitFactory(code="CSE")
    YustLegacyProfileSeeder()()
    return {
        "nursing_unit": nursing_unit,
        "nursing": ProgramFactory(org_unit=nursing_unit),
        "other": ProgramFactory(org_unit=other_unit),
        "staff": UserFactory(permissions=[Permission.REGISTRATION_HOLDS_MANAGE, Permission.SECTIONS_MANAGE]),
    }


def term_of(type_code: str) -> Any:
    today = timezone.localdate()
    term = TermFactory(
        published=True,
        start_date=today + timedelta(days=31),
        end_date=today + timedelta(days=120),
        term_type=TermType.objects.get(code=type_code),
    )
    open_window(term, TermWindowType.REGISTRATION)
    return term


def legacy_student(program: Any, admission_year: int) -> Any:
    return StudentRecordFactory(program=program, admission_date=date(admission_year, 3, 1), catalog_year=admission_year)


def refused_for(record: Any, section: Any) -> list[RuleCode]:
    section.refresh_from_db()
    outcome = EnrollStudent().handle(record, section, None)
    return [result.code for result in outcome.evaluation.results if result.blocks()]


@pytest.mark.parametrize(
    ("term_type", "program", "year", "limit"),
    [
        pytest.param("spring", "nursing", 2014, 21, id="spring, 2014 nursing (legacy bug gave 18)"),
        pytest.param("fall", "other", 2016, 18, id="fall, 2016 other"),
        pytest.param("spring", "nursing", 2013, 20, id="spring, 2013 nursing"),
        pytest.param("fall", "other", 2012, 17, id="fall, 2012 other"),
        pytest.param("summer", "nursing", 2014, 6, id="summer, 2014 nursing"),
        pytest.param("summer", "other", 2015, 5, id="summer, 2015 other"),
        pytest.param("winter", "nursing", 2013, 6, id="winter, 2013 nursing"),
        pytest.param("summer", "other", 2011, 6, id="summer, 2011 other"),
    ],
)
def test_applies_the_legacy_credit_limits_by_term_type_admission_year_and_nursing(
    legacy: dict[str, Any], term_type: str, program: str, year: int, limit: int
) -> None:
    record = legacy_student(legacy[program], year)
    policy = CreditLimitPolicy.applicable_to(record, TermType.objects.get(code=term_type).pk)

    assert policy is not None
    assert policy.max_credits == Decimal(limit)


def test_lets_a_2014_nursing_student_register_21_credits_not_18_and_leaves_credit_bank_courses_out(
    legacy: dict[str, Any],
) -> None:
    term = term_of("spring")
    record = legacy_student(legacy["nursing"], 2014)

    def section(code: str, credits: int) -> Any:
        return SectionFactory(term=term, published=True, course=CourseFactory(code=code, version={"credits": credits}))

    for index in range(1, 7):
        EnrollmentFactory(section=section(f"NUR10{index}0", 3), student_record=record)
    bank = section("0091001", 3)
    YustLegacyProfileSeeder()()  # marks credit bank courses

    assert EnrollStudent().handle(record, section("NUR1980", 3), None).succeeded()  # 21: the legacy bug refused it
    assert EnrollStudent().handle(record, section("NUR1990", 3), None).outcome == AttemptOutcome.REFUSED  # 24 > 21
    bank.refresh_from_db()
    assert EnrollStudent().handle(record, bank, None).succeeded()


def test_reproduces_the_other_legacy_checks_with_the_default_rule_set(legacy: dict[str, Any]) -> None:
    term = term_of("fall")
    record = legacy_student(legacy["other"], 2016)
    planner = UserFactory(permissions=[Permission.SECTIONS_MANAGE])

    def meet(section: Any, start: str, end: str) -> None:
        SaveSectionMeeting()(
            section, {"weekday": 2, "start_time": start, "end_time": end, "room_id": RoomFactory().pk}, planner
        )

    # TARGET_ST_DEPART / TARGET_ST_GRADE: department and admission year restrictions.
    nursing_only = SectionFactory(
        term=term, published=True, eligibility=TargetCriteria(org_unit_ids=(legacy["nursing_unit"].pk,))
    )
    from_2018 = SectionFactory(term=term, published=True, eligibility=TargetCriteria(admission_year_from=2018))
    assert refused_for(record, nursing_only) == [RuleCode.ELIGIBILITY]
    assert refused_for(record, from_2018) == [RuleCode.ELIGIBILITY]

    # SPCOURSE: prerequisite not passed.
    advanced = SectionFactory(term=term, published=True)
    CourseRequisite.objects.create(
        course_version_id=advanced.version_id, kind=RequisiteKind.PREREQUISITE, required_course=CourseFactory()
    )
    assert refused_for(record, advanced) == [RuleCode.REQUISITES]

    # Timetable conflict, then capacity (SFOP_MAX).
    first = SectionFactory(term=term, published=True, section_code="01")
    meet(first, "09:00", "10:30")
    first.refresh_from_db()
    assert EnrollStudent().handle(record, first, None).succeeded()
    overlapping = SectionFactory(term=term, published=True)
    meet(overlapping, "10:00", "11:00")
    assert refused_for(record, overlapping) == [RuleCode.TIME_CONFLICT]
    full = SectionFactory(term=term, published=True, capacity=0)
    assert refused_for(record, full) == [RuleCode.CAPACITY]

    # Already registered for the course (any section).
    same_course = SectionFactory(term=term, published=True, course=first.course, section_code="02")
    assert refused_for(record, same_course) == [RuleCode.DUPLICATE_COURSE]

    # Retake: allowed and marked (legacy SSC_RAPPLY).
    earlier_term = TermFactory(start_date=date(2020, 3, 2), end_date=date(2020, 6, 20))
    retaken = SectionFactory(term=term, published=True)
    EnrollmentFactory(
        section=SectionFactory(term=earlier_term, published=True, course=retaken.course),
        student_record=record,
        grade="D0",
    )
    retaken.refresh_from_db()
    assert EnrollStudent().handle(record, retaken, None).enrollment.is_retake

    # SRDENY: a hold blocks; SRALLOW: an override lets through.
    ManageHolds().place(record, HoldType.ADMINISTRATIVE, "Deny list", legacy["staff"])
    assert refused_for(record, SectionFactory(term=term, published=True)) == [RuleCode.HOLD]

    other = legacy_student(legacy["other"], 2016)
    ManageHolds().grant_override(
        other, term, RuleCode.ELIGIBILITY, "Allowed by the dean", legacy["staff"], section_id=nursing_only.pk
    )
    nursing_only.refresh_from_db()
    assert EnrollStudent().handle(other, nursing_only, None).succeeded()
