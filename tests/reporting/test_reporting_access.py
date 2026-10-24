"""The reporting views are ``security_invoker`` (``db/sql/views/reporting.sql``): whoever reads them
gets the row level security of the tables behind them. ``visible_to`` of the view models gives
the same rows in the application layer, checked for each of the eight views and seven kinds of
reader (porting-plan 7.4: both layers, independently)."""

from __future__ import annotations

from datetime import date, time, timedelta
from decimal import Decimal
from typing import Any

import pytest
from django.utils import timezone

from ninefruits.core.db import session_context
from ninefruits.curriculum.enums import ProgramRole
from ninefruits.grading.models import TermRecord
from ninefruits.graduation.models import DegreeAudit
from ninefruits.offering.models import SectionInstructor, SectionMeeting
from ninefruits.person.actions import AssignAdvisor
from ninefruits.reporting.models import VIEW_MODELS, ReadOnlyViewError, ReportStudent
from ninefruits.security.actions import AssignRole
from ninefruits.security.enums import Permission, ScopeType
from ninefruits.security.services.authorization import authorization
from tests.factories.offering import SectionFactory
from tests.factories.organization import OrgUnitFactory, ProgramFactory
from tests.factories.person import InstructorFactory, StudentRecordFactory, StudentStatusChangeFactory
from tests.factories.registration import EnrollmentFactory
from tests.factories.security import RoleFactory, UserFactory
from tests.factories.term import TermFactory

pytestmark = pytest.mark.django_db

READERS = ("registrar", "cse assistant", "korean program officer", "advisor", "instructor", "alice", "nobody")


@pytest.fixture
def world(essential_data: None) -> dict[str, Any]:
    eng = OrgUnitFactory(code="ENG")
    cse = OrgUnitFactory(code="CSE", parent=eng)
    kor = OrgUnitFactory(code="KOR")
    programs = {"CSE": ProgramFactory(code="B-CSE", org_unit=cse), "KOR": ProgramFactory(code="B-KOR", org_unit=kor)}
    records = {
        "alice": StudentRecordFactory(student_number="S-ALICE", program=programs["CSE"], year_level=2),
        "bob": StudentRecordFactory(student_number="S-BOB", program=programs["CSE"], year_level=3),
        "carol": StudentRecordFactory(student_number="S-CAROL", program=programs["KOR"], year_level=4),
    }
    term = TermFactory(published=True, start_date=date(2025, 3, 1), end_date=date(2025, 6, 20))
    cse_section = SectionFactory(published=True, term=term, course__org_unit=cse)
    kor_section = SectionFactory(term=term, course__org_unit=kor)
    for name, record in records.items():
        section = kor_section if name == "carol" else cse_section
        EnrollmentFactory(section=section, student_record=record, grade="A0")
        TermRecord.objects.create(
            student_record=record, term=term, cumulative_gpa=Decimal("3.5"), calculated_at=timezone.now()
        )
        StudentStatusChangeFactory(student_record=record)
        DegreeAudit.objects.create(
            student_record=record,
            program_role=ProgramRole.PRIMARY,
            program=record.program,
            is_satisfied=False,
            earned_credits=Decimal("3"),
            result={},
            audited_at=timezone.now().replace(microsecond=0),
        )
    for section in (cse_section, kor_section):
        SectionMeeting.objects.create(
            section=section,
            weekday=1,
            start_time=time(9),
            end_time=time(10, 15),
            start_date=term.start_date,
            end_date=term.end_date,
        )

    def assigned(permissions: list[Permission], scope_type: ScopeType = ScopeType.GLOBAL, scope_id: Any = None) -> Any:
        user = UserFactory()
        AssignRole()(user, RoleFactory(permissions=permissions), "test", scope_type, scope_id)
        return user

    staff = [Permission.STUDENT_RECORDS_VIEW, Permission.SECTIONS_VIEW, Permission.ENROLLMENTS_VIEW]
    users = {
        "registrar": assigned([*staff, Permission.GRADES_MANAGE]),
        "cse assistant": assigned(staff, ScopeType.ORG_UNIT, cse.pk),
        "korean program officer": assigned([Permission.STUDENT_RECORDS_VIEW], ScopeType.PROGRAM, programs["KOR"].pk),
        "alice": UserFactory(person=records["alice"].person),
        "nobody": UserFactory(),
    }
    advisor = InstructorFactory(org_unit=kor)
    users["advisor"] = UserFactory(person=advisor.person)
    AssignAdvisor().handle(records["carol"], advisor, timezone.localdate() - timedelta(days=30))
    teacher = InstructorFactory(org_unit=kor)
    users["instructor"] = UserFactory(person=teacher.person)
    SectionInstructor.objects.create(section=kor_section, instructor=teacher)
    authorization().flush()
    return {"users": users, "records": records}


def _key(view: str, row: dict[str, Any]) -> Any:
    if view == "headcount":
        return (row["org_unit_id"], row["program_id"], row["year_level"], row["status"])
    return row[VIEW_MODELS[view]._meta.pk.attname]


def _rows(view: str, queryset: Any) -> set[Any]:
    model = VIEW_MODELS[view]
    fields = ["org_unit_id", "program_id", "year_level", "status"] if view == "headcount" else [model._meta.pk.attname]
    return {_key(view, row) for row in queryset.values(*fields)}


@pytest.mark.parametrize("view", list(VIEW_MODELS))
@pytest.mark.parametrize("who", READERS)
def test_visible_to_gives_the_rows_row_level_security_gives(world: dict[str, Any], view: str, who: str) -> None:
    user = world["users"][who]
    model = VIEW_MODELS[view]
    application = _rows(view, model.objects.visible_to(user))

    context = session_context()
    context.use_baseline({})
    context.for_user(user.pk)
    database = _rows(view, model.objects.all())
    context.reset()

    assert application == database


def test_students_see_only_themselves_and_nobody_sees_nothing(world: dict[str, Any]) -> None:
    context = session_context()
    context.use_baseline({})
    context.for_user(world["users"]["alice"].pk)
    assert list(ReportStudent.objects.values_list("student_number", flat=True)) == ["S-ALICE"]
    context.for_user(world["users"]["nobody"].pk)
    assert ReportStudent.objects.count() == 0


def test_the_views_are_read_only(world: dict[str, Any]) -> None:
    row = ReportStudent.objects.get(student_number="S-ALICE")
    with pytest.raises(ReadOnlyViewError):
        row.save()
    with pytest.raises(ReadOnlyViewError):
        row.delete()


def test_translated_columns_follow_the_session_locale(world: dict[str, Any]) -> None:
    program = world["records"]["alice"].program
    program.name = {"en": "Computer Science", "ko": "컴퓨터공학"}
    program.save()
    context = session_context()
    context.set_locale("ko", "en")
    assert ReportStudent.objects.get(student_number="S-ALICE").program_name == "컴퓨터공학"
    context.set_locale("en", "en")
    row = ReportStudent.objects.get(student_number="S-ALICE")
    assert row.program_name == "Computer Science"
    assert row.program_name_i18n == {"en": "Computer Science", "ko": "컴퓨터공학"}
