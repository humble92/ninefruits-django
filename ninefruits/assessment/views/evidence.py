"""The evidence file of an external result (original ``EvidenceController``), for staff who record
or manage examinations and for the student it belongs to. Results the user cannot see (row level
security) are refused like those the policy refuses."""

from __future__ import annotations

from typing import Any

from django.core.exceptions import PermissionDenied
from django.http import HttpRequest

from ninefruits.assessment.models import AssessmentResult
from ninefruits.media.models import Media
from ninefruits.media.views import PrivateMediaDownloadView


class EvidenceDownloadView(PrivateMediaDownloadView):
    disposition = "inline"

    def get_media(self, request: HttpRequest, **kwargs: Any) -> Media | None:
        result = AssessmentResult.objects.visible_to(request.user).filter(pk=kwargs["pk"]).first()
        if result is None or not request.user.has_perm("view", result):
            raise PermissionDenied
        return result.get_first_media(AssessmentResult.EVIDENCE_COLLECTION)
