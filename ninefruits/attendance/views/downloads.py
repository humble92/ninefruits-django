"""Roster CSV and attendance sheet PDF (original ``RosterCsvController`` and
``AttendanceSheetController``), for the section's instructors and the staff who see the section.
Downloading personal data is audited (``attendance.roster_exported``,
``attendance.sheet_exported``)."""

from __future__ import annotations

from collections import defaultdict
from typing import Any

from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404
from django.template.loader import render_to_string
from django.utils import formats, timezone
from django.utils.translation import gettext as _
from django.utils.translation import pgettext
from django.views import View

from ninefruits.attendance.models import AttendanceRecord, ClassMeeting
from ninefruits.attendance.services import AttendanceSummary, SectionRoster
from ninefruits.audit.logger import audit
from ninefruits.media.services import header_safe_file_name
from ninefruits.offering.models import Section

SHEET_TEMPLATE = "attendance/pdf/attendance_sheet.html"


def _section(request: HttpRequest, pk: int) -> Section:
    section: Section = get_object_or_404(Section.objects.select_related("course", "version", "term"), pk=pk)
    SectionRoster.authorize_view(section, request.user)
    return section


def _private(response: HttpResponse) -> HttpResponse:
    response["Cache-Control"] = "private, no-store"
    response["X-Content-Type-Options"] = "nosniff"
    return response


class RosterCsvView(LoginRequiredMixin, View):
    http_method_names = ["get", "head"]

    def get(self, request: HttpRequest, pk: int) -> HttpResponse:
        section = _section(request, pk)
        audit("attendance.roster_exported", section, properties={"section_id": section.pk}, causer=request.user)
        response = HttpResponse(SectionRoster().csv(section).encode("utf-8"), content_type="text/csv; charset=UTF-8")
        file_name = header_safe_file_name(f"{section.label()}-roster.csv")
        response["Content-Disposition"] = f'attachment; filename="{file_name}"'
        return _private(response)


def sheet_marks() -> dict[str, str]:
    """The mark of each status on the sheet (legacy paper sheets: O, triangle, X)."""
    return {
        "present": _("O"),
        "late": _("△"),
        "absent": _("X"),
        "excused": pgettext("attendance.sheet.marks", "E"),
    }


def sheet_context(section: Section) -> dict[str, Any]:
    """Students down, meetings across (cancelled ones left out), the recorded statuses and the
    totals; meetings still to come are empty cells for writing by hand."""
    from ninefruits.grading.views.transcript import institution_name
    from ninefruits.offering.models import SectionInstructor

    enrollments = SectionRoster().enrollments(section)
    meetings = list(
        ClassMeeting.objects.filter(section_id=section.pk).scheduled().order_by("meeting_date", "start_time")
    )
    marks: dict[int, dict[int, str]] = defaultdict(dict)
    for record in AttendanceRecord.objects.filter(class_meeting_id__in=[m.pk for m in meetings]).only(
        "enrollment_id", "class_meeting_id", "status"
    ):
        marks[record.enrollment_id][record.class_meeting_id] = record.status
    summary = AttendanceSummary().for_section(section, enrollments)
    instructors = [
        assignment.instructor.person.display_name()
        for assignment in SectionInstructor.objects.filter(section_id=section.pk)
        .select_related("instructor__person")
        .order_by("id")
    ]
    labels = sheet_marks()
    rows = [
        {
            "number": index,
            "record": enrollment.student_record,
            "marks": [labels.get(marks[enrollment.pk].get(meeting.pk, ""), "") for meeting in meetings],
            "counts": summary["students"][enrollment.pk],
        }
        for index, enrollment in enumerate(enrollments, start=1)
    ]
    return {
        "title": _("Attendance sheet"),
        "institution": institution_name(),
        "section": section,
        "instructors": ", ".join(instructors),
        "meetings": meetings,
        "rows": rows,
        "printed": formats.date_format(timezone.localdate(), "DATE_FORMAT"),
    }


class AttendanceSheetView(LoginRequiredMixin, View):
    http_method_names = ["get", "head"]

    def get(self, request: HttpRequest, pk: int) -> HttpResponse:
        from ninefruits.pdf import PdfOptions, PdfRenderingError, get_renderer

        section = _section(request, pk)
        audit("attendance.sheet_exported", section, properties={"section_id": section.pk}, causer=request.user)
        html = render_to_string(SHEET_TEMPLATE, sheet_context(section), request=request)
        try:
            pdf = get_renderer().render(html, PdfOptions(landscape=True))
        except PdfRenderingError:
            return HttpResponse(
                _("The PDF could not be created. Try again later."), status=503, content_type="text/plain"
            )
        response = HttpResponse(pdf, content_type="application/pdf")
        file_name = header_safe_file_name(f"{section.label()}-attendance.pdf")
        response["Content-Disposition"] = f'inline; filename="{file_name}"'
        return _private(response)
