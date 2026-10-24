""" "Issue certificate" on a student record (original ``IssueCertificateAction`` header action of
``ViewStudentRecord``): kind, language, purpose and copies. ``StudentRecordAdmin`` mixes this in
and lists ``issue_certificate`` in ``actions_detail``. When done, the record page shows the
serial number with a link to the PDF (the original opened it in a new tab)."""

from __future__ import annotations

from typing import Any

from django.contrib import messages
from django.core.exceptions import ValidationError
from django.http import HttpRequest, HttpResponse, HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.urls import reverse
from django.utils.html import format_html
from django.utils.translation import gettext
from django.utils.translation import gettext_lazy as _
from unfold.decorators import action

from .common import IssueCertificateForm


class IssueCertificateActionMixin:
    """For ``StudentRecordAdmin`` (a ``ModelAdmin`` of ``person.StudentRecord``)."""

    def has_issue_certificate_permission(self, request: HttpRequest, object_id: Any = None) -> bool:
        from ninefruits.certificate.actions import can_issue

        return object_id is not None and can_issue(request.user)

    @action(
        description=_("Issue certificate"),
        url_path="issue-certificate",
        permissions=["issue_certificate"],
        icon="note_add",
    )
    def issue_certificate(self, request: HttpRequest, object_id: Any) -> HttpResponse:
        from ninefruits.certificate.actions import IssueCertificate
        from ninefruits.institution.admin_support import admin_url, render_action_form
        from ninefruits.pdf import PdfRenderingError
        from ninefruits.person.models import StudentRecord

        record = get_object_or_404(StudentRecord.objects.visible_to(request.user), pk=object_id)
        back = admin_url(record)
        form = IssueCertificateForm(request.POST or None)
        if request.method == "POST" and form.is_valid():
            data = form.cleaned_data
            try:
                issue = IssueCertificate().handle(
                    record, data["certificate_type"], data["locale"], request.user, data.get("purpose"), data["copies"]
                )
            except ValidationError as error:
                if hasattr(error, "error_dict"):
                    for field, errors in error.message_dict.items():
                        form.add_error(field if field in form.fields else None, errors)
                else:
                    form.add_error(None, error.messages)
            except PdfRenderingError:
                form.add_error(None, gettext("The PDF could not be created. Try again later."))
            else:
                messages.success(
                    request,
                    format_html(
                        '{} <a class="underline" href="{}" target="_blank" rel="noopener">{}</a>',
                        gettext("Certificate %(serial)s issued.") % {"serial": issue.serial_number},
                        reverse("certificate:download", args=[issue.pk]),
                        gettext("PDF"),
                    ),
                )
                return HttpResponseRedirect(back)
        return render_action_form(
            self, request, form, _("Issue certificate"), back, subtitle=f"{record} · {record.person.display_name()}"
        )
