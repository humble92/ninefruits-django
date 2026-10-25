"""The standard reports (original ``App\\Domain\\Reporting\\Services\\ReportCatalog``, ADR 0016):
each is a reporting view, the parameters it takes and the columns it shows. No business rule
lives here; the views and the caller's row level security decide what comes back.

Only the listed reports, parameters and columns exist: the column and ordering names come from
``REPORTS`` (an allow-list), never from the request (porting-plan 11). CSV cells that a
spreadsheet would run as a formula are neutralised (``cell``)."""

from __future__ import annotations

import csv
import io
import re
from collections.abc import Iterator
from dataclasses import dataclass
from datetime import UTC, date, datetime
from typing import Any

from django.db.models import Exists, OuterRef, QuerySet
from django.http import Http404
from django.utils import timezone
from django.utils.functional import Promise
from django.utils.translation import gettext_lazy as _
from django.utils.translation import pgettext_lazy

from ninefruits.reporting.models import VIEW_MODELS

#: Request parameters a report may take (original ``$request->only([...])``).
PARAMETERS = ("org_unit", "status", "year_level", "term", "standing", "satisfied", "date_from", "date_to")

#: Rows on screen and in a CSV (original ``rows(limit: 500)`` on the page, 100000 in the CSV).
SCREEN_LIMIT = 500
CSV_LIMIT = 100_000

_FORMULA = re.compile(r"^[=+\-@\t\r]")


@dataclass(frozen=True)
class ReportDefinition:
    view: str
    params: tuple[str, ...]
    columns: tuple[str, ...]
    order: tuple[str, ...]


REPORTS: dict[str, ReportDefinition] = {
    "students": ReportDefinition(
        "students",
        ("org_unit", "status", "year_level"),
        (
            "student_number",
            "student_name",
            "program_name",
            "org_unit_name",
            "year_level",
            "status",
            "admission_date",
            "graduation_date",
            "degree_number",
        ),
        ("student_number",),
    ),
    "headcount": ReportDefinition(
        "headcount",
        ("org_unit", "status"),
        ("org_unit_code", "org_unit_name", "program_code", "program_name", "year_level", "status", "students"),
        ("org_unit_code", "program_code", "year_level", "status"),
    ),
    "term_records": ReportDefinition(
        "term_records",
        ("term", "standing"),
        (
            "student_number",
            "term_code",
            "attempted_credits",
            "earned_credits",
            "term_gpa",
            "cumulative_earned_credits",
            "cumulative_gpa",
            "academic_standing",
            "warning_count",
            "is_honors",
            "honors_rank",
        ),
        ("student_number",),
    ),
    "graduation_candidates": ReportDefinition(
        "degree_audits",
        ("satisfied",),
        (
            "student_number",
            "program_code",
            "program_name",
            "program_role",
            "is_satisfied",
            "earned_credits",
            "required_credits",
            "cumulative_gpa",
            "audited_at",
        ),
        ("student_number",),
    ),
    "status_changes": ReportDefinition(
        "status_changes",
        ("term", "date_from", "date_to"),
        (
            "student_number",
            "type_name",
            "from_status",
            "to_status",
            "effective_date",
            "term_code",
            "status",
            "decided_at",
        ),
        ("effective_date", "student_number"),
    ),
    "section_enrollments": ReportDefinition(
        "section_enrollments",
        ("term", "org_unit"),
        (
            "term_code",
            "course_code",
            "course_title",
            "section_code",
            "org_unit_name",
            "instructors",
            "status",
            "capacity",
            "enrolled",
            "waiting",
        ),
        ("course_code", "section_code"),
    ),
    "not_registered": ReportDefinition(
        "students",
        ("term", "org_unit"),
        ("student_number", "student_name", "program_name", "org_unit_name", "year_level", "status"),
        ("student_number",),
    ),
}

#: Report names (original ``graduation.reports.names.*``).
REPORT_NAMES: dict[str, Promise] = {
    "students": _("Student list"),
    "headcount": _("Headcount by unit, program, year and status"),
    "term_records": _("Term grade summary (warnings, honors)"),
    "graduation_candidates": _("Graduation candidates (latest audit)"),
    "status_changes": _("Status changes"),
    "section_enrollments": _("Enrollment per section"),
    "not_registered": _("Students not registered in a term"),
}

#: Column headings (original ``graduation.report_columns.*``).
COLUMN_LABELS: dict[str, Promise] = {
    "student_number": _("Student number"),
    "student_name": pgettext_lazy("graduation", "Name"),
    "program_name": pgettext_lazy("graduation", "Program"),
    "program_code": _("Program code"),
    "program_role": pgettext_lazy("graduation", "Role"),
    "org_unit_name": _("Unit"),
    "org_unit_code": _("Unit code"),
    "year_level": pgettext_lazy("graduation", "Year"),
    "status": pgettext_lazy("graduation", "Status"),
    "admission_date": pgettext_lazy("graduation", "Admitted"),
    "graduation_date": pgettext_lazy("graduation", "Graduated"),
    "degree_number": _("Degree number"),
    "students": pgettext_lazy("graduation", "Students"),
    "term_code": _("Term"),
    "attempted_credits": _("Attempted"),
    "earned_credits": _("Earned"),
    "term_gpa": _("Term GPA"),
    "cumulative_earned_credits": _("Cumulative earned"),
    "cumulative_gpa": pgettext_lazy("graduation", "Cumulative GPA"),
    "academic_standing": _("Standing"),
    "warning_count": _("Warnings"),
    "is_honors": pgettext_lazy("graduation", "Honors"),
    "honors_rank": pgettext_lazy("graduation", "Honors rank"),
    "is_satisfied": _("Satisfied"),
    "required_credits": pgettext_lazy("graduation", "Required"),
    "audited_at": _("Audited"),
    "type_name": pgettext_lazy("graduation", "Change"),
    "from_status": _("From"),
    "to_status": _("To"),
    "effective_date": _("Effective"),
    "decided_at": pgettext_lazy("graduation", "Decided"),
    "course_code": pgettext_lazy("graduation.report_columns", "Course"),
    "course_title": pgettext_lazy("graduation", "Title"),
    "section_code": pgettext_lazy("graduation", "Section"),
    "instructors": pgettext_lazy("graduation", "Instructors"),
    "capacity": pgettext_lazy("graduation", "Capacity"),
    "enrolled": pgettext_lazy("graduation", "Enrolled"),
    "waiting": pgettext_lazy("graduation", "Waiting"),
}


def timestamp_text(value: datetime) -> str:
    """A ``timestamptz`` as the original wrote it: PostgreSQL's text form in UTC with the offset,
    ``2026-10-24 07:26:59+00`` (fractional seconds only when there are any, trailing zeros
    dropped, as PostgreSQL prints them)."""
    if timezone.is_naive(value):
        return str(value)
    utc = value.astimezone(UTC)
    fraction = f".{utc.microsecond:06d}".rstrip("0") if utc.microsecond else ""
    return f"{utc:%Y-%m-%d %H:%M:%S}{fraction}+00"


def cell(value: Any) -> str:
    """A CSV or screen cell: ``''`` for none, ``Y``/``N`` for booleans, the text otherwise. A cell
    starting with ``=``, ``+``, ``-``, ``@``, a tab or a carriage return would run as a formula
    in a spreadsheet (CSV injection), so it gets a leading apostrophe. Times are written like the
    original (``timestamp_text``), dates as ``YYYY-MM-DD``."""
    if value is None:
        text = ""
    elif isinstance(value, bool):
        text = "Y" if value else "N"
    elif isinstance(value, datetime):
        text = timestamp_text(value)
    elif isinstance(value, date):
        text = value.isoformat()
    else:
        text = str(value)
    return "'" + text if _FORMULA.match(text) else text


class ReportCatalog:
    REPORTS = REPORTS

    @staticmethod
    def keys() -> list[str]:
        return list(REPORTS)

    @staticmethod
    def definition(key: str) -> ReportDefinition:
        try:
            return REPORTS[key]
        except KeyError:
            raise Http404(f"Unknown report [{key}].") from None

    @staticmethod
    def name(key: str) -> str:
        return str(REPORT_NAMES[key])

    @staticmethod
    def column_label(column: str) -> str:
        return str(COLUMN_LABELS[column])

    @classmethod
    def params_of(cls, key: str, data: Any) -> dict[str, Any]:
        """The parameters of the report present in ``data`` (a dict or ``QueryDict``)."""
        definition = cls.definition(key)
        return {name: data.get(name) for name in definition.params if data.get(name) not in (None, "")}

    def rows(self, key: str, params: dict[str, Any], limit: int = 5000) -> list[dict[str, Any]]:
        return list(self.query(key, params)[:limit])

    def query(self, key: str, params: dict[str, Any]) -> Any:
        """The view's rows as dicts of the report's columns, filtered by its parameters."""
        from ninefruits.organization.models import OrgUnit
        from ninefruits.registration.enums import EnrollmentStatus
        from ninefruits.registration.models import Enrollment
        from ninefruits.term.models import Term

        definition = self.definition(key)
        model = VIEW_MODELS[definition.view]
        # Each view model has its own columns; the filters below are checked against the report.
        queryset: QuerySet[Any] = model._default_manager.all()

        org_unit_ids: list[int] | None = None
        if params.get("org_unit") not in (None, ""):
            root = int(params["org_unit"])
            org_unit_ids = sorted({root, *OrgUnit.descendant_ids_of([root])})

        if key == "not_registered":
            term_id = _int(params.get("term")) or 0
            registered = Enrollment.objects.filter(
                student_record_id=OuterRef("student_record_id"),
                term_id=term_id,
                status__in=[EnrollmentStatus.ENROLLED, EnrollmentStatus.COMPLETED],
            )
            queryset = queryset.filter(status="enrolled").filter(~Exists(registered))

        for param in definition.params:
            value = params.get(param)
            if value in (None, "") or (key == "not_registered" and param == "term"):
                continue
            if param == "org_unit":
                if definition.view == "section_enrollments":
                    # The view has the unit's code, not its id.
                    codes = OrgUnit.objects.filter(pk__in=org_unit_ids or []).values_list("code", flat=True)
                    queryset = queryset.filter(org_unit_code__in=list(codes))
                else:
                    queryset = queryset.filter(org_unit_id__in=org_unit_ids or [])
            elif param == "status":
                queryset = queryset.filter(status=str(value))
            elif param == "year_level":
                queryset = queryset.filter(year_level=int(value))
            elif param == "term":
                term = Term.objects.filter(pk=_int(value) or 0).first()
                if term is None:
                    raise Http404("Unknown term.")
                queryset = queryset.filter(term_code=term.code)
            elif param == "standing":
                queryset = queryset.filter(academic_standing=str(value))
            elif param == "satisfied":
                queryset = queryset.filter(is_satisfied=value == "yes")
            elif param == "date_from":
                queryset = queryset.filter(effective_date__gte=value)
            elif param == "date_to":
                queryset = queryset.filter(effective_date__lte=value)

        return queryset.order_by(*definition.order).values(*definition.columns)

    def csv_lines(self, key: str, params: dict[str, Any], limit: int = CSV_LIMIT) -> Iterator[str]:
        """UTF-8 CSV with a byte order mark, header first, one line per row."""
        columns = self.definition(key).columns
        buffer = io.StringIO()
        writer = csv.writer(buffer, lineterminator="\n")

        def line(values: list[str]) -> str:
            buffer.seek(0)
            buffer.truncate(0)
            writer.writerow(values)
            return buffer.getvalue()

        yield "﻿" + line([self.column_label(column) for column in columns])
        for row in self.query(key, params)[:limit].iterator(chunk_size=2000):
            yield line([cell(row.get(column)) for column in columns])

    def csv(self, key: str, params: dict[str, Any], limit: int = CSV_LIMIT) -> str:
        return "".join(self.csv_lines(key, params, limit))


def _int(value: Any) -> int | None:
    try:
        return int(value)
    except TypeError, ValueError:
        return None
