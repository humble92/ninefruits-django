"""The standard report catalog (original ``ReportCatalog``): the spreadsheet formula guard of the
original ``tests/Feature/Security/HardeningTest.php`` ("neutralises spreadsheet formulas in CSV
cells"), the CSV format, the column and parameter allow-lists, the filters, and the reports page
and CSV download access."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Any
from zoneinfo import ZoneInfo

import pytest
from django.http import Http404
from django.test import Client
from django.utils import timezone

from ninefruits.audit.models import ActivityLog, SecurityEvent
from ninefruits.audit.security_events import SecurityEventType
from ninefruits.core.db import session_context
from ninefruits.reporting.services import REPORTS, ReportCatalog
from ninefruits.reporting.services.catalog import COLUMN_LABELS, REPORT_NAMES, cell
from ninefruits.security.enums import Permission
from tests.factories.offering import SectionFactory
from tests.factories.organization import OrgUnitFactory, ProgramFactory
from tests.factories.person import PersonFactory, StudentRecordFactory
from tests.factories.security import UserFactory
from tests.factories.term import TermFactory


def test_neutralises_spreadsheet_formulas_in_csv_cells() -> None:
    """Original ``HardeningTest``: ``ReportCatalog::cell``."""
    assert cell("=1+1") == "'=1+1"
    assert cell("+123") == "'+123"
    assert cell("-5") == "'-5"
    assert cell("@x") == "'@x"
    assert cell("\tTAB") == "'\tTAB"
    assert cell("\rCR") == "'\rCR"
    assert cell("plain") == "plain"
    assert cell(None) == ""
    assert cell(True) == "Y"
    assert cell(False) == "N"
    assert cell(Decimal("3.50")) == "3.50"
    assert cell(date(2026, 2, 20)) == "2026-02-20"
    assert cell(Decimal("-1.5")) == "'-1.5"


def test_every_report_has_a_name_and_labelled_allow_listed_columns() -> None:
    assert set(REPORT_NAMES) == set(REPORTS) == set(ReportCatalog.keys())
    assert len(REPORTS) == 7
    for definition in REPORTS.values():
        assert set(definition.columns) <= set(COLUMN_LABELS)
        assert set(definition.order) <= set(definition.columns) | {"effective_date"}


@pytest.mark.django_db
def test_returns_only_the_report_columns_and_ignores_unknown_parameters(essential_data: None) -> None:
    record = StudentRecordFactory()
    rows = ReportCatalog().rows("students", {"status": "enrolled", "birth_date": "2000-01-01", "order": "x"})
    assert [row["student_number"] for row in rows] == [record.student_number]
    assert set(rows[0]) == set(REPORTS["students"].columns)
    with pytest.raises(Http404):
        ReportCatalog().rows("nope", {})


@pytest.mark.django_db
def test_filters_by_org_unit_and_its_descendants(essential_data: None) -> None:
    eng = OrgUnitFactory(code="ENG")
    cse = OrgUnitFactory(code="CSE", parent=eng)
    kor = OrgUnitFactory(code="KOR")
    in_cse = StudentRecordFactory(program=ProgramFactory(org_unit=cse))
    StudentRecordFactory(program=ProgramFactory(org_unit=kor))
    catalog = ReportCatalog()
    assert [row["student_number"] for row in catalog.rows("students", {"org_unit": eng.pk})] == [in_cse.student_number]
    assert [row["org_unit_code"] for row in catalog.rows("headcount", {"org_unit": eng.pk})] == ["CSE"]

    term = TermFactory(published=True, start_date=date(2025, 3, 1), end_date=date(2025, 6, 20))
    SectionFactory(term=term, course__org_unit=cse)
    SectionFactory(term=term, course__org_unit=kor)
    # The section view names the unit by code; the filter still takes the unit and those below it.
    rows = catalog.rows("section_enrollments", {"term": term.pk, "org_unit": eng.pk})
    assert len(rows) == 1
    with pytest.raises(Http404):
        catalog.rows("section_enrollments", {"term": 0})


@pytest.mark.django_db
def test_writes_a_csv_with_a_byte_order_mark_labels_and_guarded_cells(essential_data: None) -> None:
    person = PersonFactory(family_name="=HYPERLINK(1)", given_name="Eve", name_variants=None)
    record = StudentRecordFactory(person=person)
    text = ReportCatalog().csv("students", {})
    assert text.startswith("﻿Student number,Name,Program,")
    line = next(line for line in text.splitlines() if record.student_number in line)
    assert ",'=HYPERLINK(1) Eve," in line
    assert text.count("\n") == 2


@pytest.mark.django_db
def test_lists_students_not_registered_in_a_term(essential_data: None) -> None:
    from tests.factories.registration import EnrollmentFactory

    term = TermFactory(published=True)
    registered = StudentRecordFactory()
    EnrollmentFactory(section=SectionFactory(published=True, term=term), student_record=registered)
    idle = StudentRecordFactory()
    StudentRecordFactory(graduated=True)
    rows = ReportCatalog().rows("not_registered", {"term": term.pk})
    assert [row["student_number"] for row in rows] == [idle.student_number]


@pytest.mark.django_db
def test_report_screens_need_the_reports_permission(essential_data: None) -> None:
    # The rows follow row level security: the reader also needs to see the student records.
    allowed = UserFactory(
        permissions=[Permission.ADMIN_PANEL_ACCESS, Permission.REPORTS_VIEW, Permission.STUDENT_RECORDS_VIEW]
    )
    denied = UserFactory(permissions=[Permission.ADMIN_PANEL_ACCESS])
    StudentRecordFactory(student_number="S-REPORT")

    def client_for(user: Any) -> Client:
        client = Client()
        client.force_login(user)
        session_context().reset()
        return client

    assert client_for(denied).get("/admin/reports/").status_code == 403
    assert client_for(denied).get("/reports/students.csv").status_code == 403
    assert Client().get("/reports/students.csv").status_code == 302

    client = client_for(allowed)
    page = client.get("/admin/reports/", {"report": "students"})
    assert page.status_code == 200
    content = page.content.decode()
    assert "S-REPORT" in content
    assert "/reports/students.csv" in content
    # A report with a term shows nothing until a term is chosen.
    assert (
        "No rows. Choose the filters above."
        in client.get("/admin/reports/", {"report": "term_records"}).content.decode()
    )
    # An unknown report falls back to the student list.
    assert client.get("/admin/reports/", {"report": "nope"}).status_code == 200

    response = client.get("/reports/students.csv", {"year_level": "1"})
    assert response["Content-Disposition"] == f'attachment; filename="students-{timezone.localdate():%Y%m%d}.csv"'
    assert response["Cache-Control"] == "private, no-store"
    exported = ActivityLog.objects.filter(event="reports.exported").latest("id")
    assert exported.properties == {"report": "students", "params": {"year_level": "1"}}
    event = SecurityEvent.objects.filter(type=SecurityEventType.DATA_EXPORTED).latest("id")
    assert event.user_id == allowed.pk
    assert event.properties["report"] == "students"
    assert event.properties["rows"] == 1


def test_cells_write_times_like_postgresql_text_in_utc() -> None:
    """The original wrote ``timestamptz`` cells as PostgreSQL text: UTC with the offset."""
    moment = datetime(2026, 10, 24, 16, 26, 59, tzinfo=ZoneInfo("Asia/Seoul"))
    assert cell(moment) == "2026-10-24 07:26:59+00"
    assert cell(moment.replace(microsecond=120000)) == "2026-10-24 07:26:59.12+00"
