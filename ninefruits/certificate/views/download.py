"""The stored PDF of an issued certificate (original ``DownloadCertificateController``): for staff
who may see the issue and for the holder; a revoked certificate only for staff who issue. The
file is the one stored at issue time (or by "Render again"), streamed from the private storage."""

from __future__ import annotations

from typing import Any, ClassVar, Literal

from django.core.exceptions import PermissionDenied
from django.http import HttpRequest
from django.shortcuts import get_object_or_404

from ninefruits.certificate.models import CertificateIssue
from ninefruits.media.models import Media
from ninefruits.media.views import PrivateMediaDownloadView


class CertificateDownloadView(PrivateMediaDownloadView):
    disposition: ClassVar[Literal["attachment", "inline"]] = "inline"

    def get_media(self, request: HttpRequest, **kwargs: Any) -> Media | None:
        issue: CertificateIssue = get_object_or_404(CertificateIssue.objects.visible_to(request.user), pk=kwargs["pk"])
        if not request.user.has_perm("download", issue):
            raise PermissionDenied
        self.issue = issue
        return issue.pdf()

    def get_file_name(self, media: Media) -> str:
        return f"{self.issue.serial_number}.pdf"

    def get_content_type(self, media: Media) -> str:
        return "application/pdf"
