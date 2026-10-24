"""The student's certificates (original Livewire ``MyCertificates``): issued by staff (porting-plan
17.5), listed newest first with a link to the stored PDF."""

from __future__ import annotations

from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import Http404, HttpRequest, HttpResponse
from django.shortcuts import render
from django.utils.translation import gettext as _
from django.views import View

from ninefruits.certificate.models import CertificateIssue
from ninefruits.certificate.services.serials import institution_now


class MyCertificatesView(LoginRequiredMixin, View):
    template_name = "certificate/portal/my_certificates.html"

    def get(self, request: HttpRequest) -> HttpResponse:
        from ninefruits.person.services import CurrentStudentRecord

        record = CurrentStudentRecord(request.session).get(request.user)
        if record is None:
            raise Http404
        issues = list(
            CertificateIssue.objects.visible_to(request.user)
            .filter(student_record_id=record.pk)
            .select_related("certificate_type")
            .order_by("-issued_at", "-id")
        )
        rows = [
            {
                "issue": issue,
                "issued_on": institution_now(issue.issued_at).date(),
                "type_name": issue.certificate_type.name_in(issue.locale),
                "can_download": not issue.is_revoked,
            }
            for issue in issues
        ]
        return render(request, self.template_name, {"title": _("My certificates"), "record": record, "rows": rows})
