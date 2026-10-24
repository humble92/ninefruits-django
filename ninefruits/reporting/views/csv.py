"""A standard report as CSV (original ``ReportCsvController``, ``/reports/{report}.csv``). Needs
``reports.view``; the rows are those the user's row level security lets the reporting view
return. Every export is audited twice: the business audit ``reports.exported`` (as the original)
and, because a report is a bulk export of personal data, the security event ``data.exported``
with the row count (porting-plan 11.2)."""

from __future__ import annotations

from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from django.http import Http404, HttpRequest, HttpResponse
from django.utils import timezone
from django.views import View

from ninefruits.audit.logger import audit
from ninefruits.audit.security_events import SecurityEventType, record_security_event
from ninefruits.reporting.services import REPORTS, ReportCatalog
from ninefruits.reporting.services.catalog import PARAMETERS
from ninefruits.security.enums import Permission


class ReportCsvView(LoginRequiredMixin, View):
    http_method_names = ["get", "head"]

    def get(self, request: HttpRequest, report: str) -> HttpResponse:
        if not request.user.has_perm(Permission.REPORTS_VIEW):
            raise PermissionDenied
        if report not in REPORTS:
            raise Http404
        params = {name: request.GET[name] for name in PARAMETERS if request.GET.get(name) not in (None, "")}
        audit("reports.exported", None, properties={"report": report, "params": params}, causer=request.user)
        lines = list(ReportCatalog().csv_lines(report, params))
        record_security_event(
            SecurityEventType.DATA_EXPORTED,
            user=request.user,
            properties={"report": report, "params": params, "rows": len(lines) - 1},
        )
        response = HttpResponse("".join(lines).encode("utf-8"), content_type="text/csv; charset=UTF-8")
        response["Content-Disposition"] = f'attachment; filename="{report}-{timezone.localdate():%Y%m%d}.csv"'
        response["Cache-Control"] = "private, no-store"
        response["X-Content-Type-Options"] = "nosniff"
        return response
