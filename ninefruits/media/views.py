"""Permission checked file downloads (original download controllers: application documents,
assessment evidence, person photos, certificate PDFs).

    class EvidenceDownloadView(PrivateMediaDownloadView):
        disposition = "inline"

        def get_media(self, request, **kwargs):
            result = get_object_or_404(AssessmentResult.objects.visible_to(request.user), pk=kwargs["pk"])
            if not request.user.has_perm("assessments.view", result):
                raise PermissionDenied
            return result.get_first_media(AssessmentResult.EVIDENCE_COLLECTION)

Files are streamed from the private storage with ``X-Content-Type-Options: nosniff``, a
private cache policy and a header-safe file name; never from a public URL."""

from __future__ import annotations

from typing import Any, ClassVar, Literal

from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import FileResponse, Http404, HttpRequest
from django.views import View

from ninefruits.media.models import Media
from ninefruits.media.services import header_safe_file_name, open_media


class PrivateMediaDownloadView(LoginRequiredMixin, View):
    """Subclasses implement :meth:`get_media` (authorization first) and may override
    :meth:`get_file_name` and :meth:`get_content_type`."""

    disposition: ClassVar[Literal["attachment", "inline"]] = "attachment"
    cache_control: ClassVar[str] = "private, no-store"
    http_method_names: ClassVar[list[str]] = ["get", "head"]  # type: ignore[misc]

    def get_media(self, request: HttpRequest, **kwargs: Any) -> Media | None:
        """Checks permissions (raise ``PermissionDenied``) and returns the file, or ``None``
        when there is none (404)."""
        raise NotImplementedError

    def get_file_name(self, media: Media) -> str:
        return media.file_name

    def get_content_type(self, media: Media) -> str:
        return media.mime_type or "application/octet-stream"

    def get(self, request: HttpRequest, **kwargs: Any) -> FileResponse:
        media = self.get_media(request, **kwargs)
        if media is None:
            raise Http404
        try:
            handle = open_media(media)
        except FileNotFoundError as error:
            raise Http404 from error
        response = FileResponse(
            handle,
            content_type=self.get_content_type(media),
            as_attachment=self.disposition == "attachment",
            filename=header_safe_file_name(self.get_file_name(media)),
        )
        response["X-Content-Type-Options"] = "nosniff"
        response["Cache-Control"] = self.cache_control
        return response
