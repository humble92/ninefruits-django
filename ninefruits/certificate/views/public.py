"""Public verification page (original ``VerifyCertificateController``): the QR code on every
certificate points here. No sign-in, 30 requests a minute per address (original
``throttle:30,1``, answered with 429), ``noindex``, and only what the paper shows."""

from __future__ import annotations

from django.http import HttpRequest, HttpResponse
from django.shortcuts import render
from django.utils.translation import gettext as _
from django.views import View
from django_ratelimit.core import is_ratelimited

from ninefruits.certificate.services.serials import institution_now
from ninefruits.certificate.services.verification import CertificateVerification

RATE = "30/m"


class VerifyCertificateView(View):
    template_name = "certificate/verify.html"
    http_method_names = ["get", "head"]

    def get(self, request: HttpRequest, code: str | None = None) -> HttpResponse:
        if is_ratelimited(request, group="certificate.verify", key="ip", rate=RATE, increment=True):
            return HttpResponse(
                _("Too many requests. Wait a minute and try again."), status=429, content_type="text/plain"
            )
        code = (code if code is not None else request.GET.get("code", "")).strip()
        result = CertificateVerification().check(code) if code else None
        issue = result.issue if result is not None else None
        context = {
            "title": _("Certificate verification"),
            "code": code,
            "result": result,
            "type_name": issue.certificate_type.name_in(issue.locale) if issue is not None else "",
            "issued_on": institution_now(issue.issued_at).date() if issue is not None else None,
        }
        response = render(request, self.template_name, context)
        response["X-Robots-Tag"] = "noindex"
        return response
