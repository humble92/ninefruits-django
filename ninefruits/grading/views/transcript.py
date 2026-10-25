"""The grade report (unofficial transcript; original ``TranscriptController``). The official,
issued transcript is a certificate (Phase 8). Students print their own unless a hold blocks
grades; staff with ``grades.view`` print records they can see (recorded as
``transcript.viewed``). ``?format=pdf`` renders the same report as a PDF through Gotenberg
(``ninefruits.pdf``); otherwise it is a printable HTML page."""

from __future__ import annotations

from typing import Any

from django.conf import settings
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from django.http import Http404, HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, render
from django.template.loader import render_to_string
from django.utils import formats, timezone
from django.utils.translation import gettext as _
from django.views import View

from ninefruits.audit.logger import audit
from ninefruits.grading.services.report import GradeReport, hidden_term_ids
from ninefruits.security.enums import Permission
from ninefruits.term.services import TermResolver

TEMPLATE = "grading/transcript.html"


def institution_name() -> str:
    from ninefruits.settings.groups.institution import InstitutionSettings

    try:
        name = InstitutionSettings.load().name
    except LookupError:
        return str(settings.APP_NAME)
    if isinstance(name, dict):
        from django.utils.translation import get_language

        language = get_language() or settings.LANGUAGE_CODE
        return str(name.get(language) or name.get(settings.LANGUAGE_CODE) or next(iter(name.values()), "")) or str(
            settings.APP_NAME
        )
    return str(name or settings.APP_NAME)


def transcript_context(
    record: Any, hidden: list[int] | None = None, report: GradeReport | None = None
) -> dict[str, Any]:
    report = report or GradeReport()
    terms = report.terms(record, hidden)
    return {
        "title": f"{_('Grade report')} {record.student_number}",
        "institution": institution_name(),
        "record": record,
        "terms": terms,
        "superseded": report.superseded(record),
        "latest": terms[-1].record if terms else None,
        "printed_at": formats.date_format(timezone.localtime(timezone.now(), TermResolver().zone()), "DATETIME_FORMAT"),
    }


def respond(request: HttpRequest, record: Any, context: dict[str, Any]) -> HttpResponse:
    if request.GET.get("format") == "pdf":
        from ninefruits.pdf import PdfRenderingError, get_renderer

        html = render_to_string(TEMPLATE, {**context, "pdf": True}, request=request)
        try:
            pdf = get_renderer().render(html)
        except PdfRenderingError:
            return HttpResponse(
                _("The PDF could not be created. Try again later."), status=503, content_type="text/plain"
            )
        response = HttpResponse(pdf, content_type="application/pdf")
        response["Content-Disposition"] = f'inline; filename="transcript-{record.student_number}.pdf"'
        return response
    return render(request, TEMPLATE, context)


class OwnTranscriptView(LoginRequiredMixin, View):
    """``/portal/grades/transcript/``: the student's own report."""

    def get(self, request: HttpRequest) -> HttpResponse:
        from ninefruits.person.services import CurrentStudentRecord

        record = CurrentStudentRecord(request.session).get(request.user)
        if record is None:
            raise Http404
        report = GradeReport()
        if report.blocking_hold(record) is not None:
            raise PermissionDenied
        return respond(request, record, transcript_context(record, hidden_term_ids(record), report))


class StaffTranscriptView(LoginRequiredMixin, View):
    """``/student-records/<id>/transcript/``: a record the staff member can see."""

    def get(self, request: HttpRequest, pk: int) -> HttpResponse:
        from ninefruits.person.models import StudentRecord

        if not request.user.has_perm(Permission.GRADES_VIEW):
            raise PermissionDenied
        record = get_object_or_404(
            StudentRecord.objects.visible_to(request.user).select_related("person", "program"), pk=pk
        )
        audit("transcript.viewed", record, properties={"student_number": record.student_number}, causer=request.user)
        return respond(request, record, transcript_context(record))
