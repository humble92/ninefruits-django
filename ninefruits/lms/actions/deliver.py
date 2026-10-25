"""What a platform reports back through the API (porting-plan 12: LMS platform callbacks).

- :meth:`RecordPlatformCallback.sync_result`: the outcome of a step the platform processed on its
  side (a queued log row is finished, or a new row is written). A course result also updates the
  course link (linked with the platform's id and URL, or failed with the message).
- :meth:`RecordPlatformCallback.deliver_scores`: the course's final scores, kept as a
  ``grades.delivered`` log step. They stay a draft: the grade entry screen's **Load scores from
  the LMS** reads the latest delivery (``PullGrades``); nothing is saved to the grades.

The caller needs ``lms.manage`` (an integration token of a service account with that permission);
the writes are platform data and run in the system context."""

from __future__ import annotations

from decimal import Decimal, InvalidOperation
from typing import Any

from django.core.exceptions import PermissionDenied, ValidationError
from django.utils import timezone
from django.utils.translation import gettext as _

from ninefruits.core.db import session_context
from ninefruits.lms.enums import LinkStatus, SyncOperation, SyncStatus
from ninefruits.lms.models import LmsCourseLink, LmsPlatform, LmsSyncLog, LmsUserLink
from ninefruits.lms.services.sync_logger import MESSAGE_MAX, SyncLogger
from ninefruits.security.enums import Permission

from .sync_section import account_of, enrolled

#: Operations a platform may report the outcome of.
REPORTABLE = (
    SyncOperation.COURSE_SYNC,
    SyncOperation.ENROLLMENT_ADD,
    SyncOperation.ENROLLMENT_REMOVE,
    SyncOperation.RECONCILE,
)
FINAL_STATUSES = (SyncStatus.SUCCEEDED, SyncStatus.FAILED, SyncStatus.SKIPPED)
MAX_SCORES = 5000


def _authorize(actor: Any) -> None:
    if actor is None or not actor.has_perm(Permission.LMS_MANAGE):
        raise PermissionDenied


def _score(value: Any) -> float:
    if isinstance(value, bool):
        raise ValidationError(_("Each score must be a number from 0 to 100."))
    try:
        number = Decimal(str(value))
    except InvalidOperation as error:
        raise ValidationError(_("Each score must be a number from 0 to 100.")) from error
    if not number.is_finite() or number < 0 or number > 100:
        raise ValidationError(_("Each score must be a number from 0 to 100."))
    return float(number)


class RecordPlatformCallback:
    def __init__(self, log: SyncLogger | None = None) -> None:
        self.log = log or SyncLogger()

    def sync_result(
        self,
        platform: LmsPlatform,
        actor: Any,
        *,
        operation: str,
        status: str,
        message: str | None = None,
        log_id: int | None = None,
        section_id: int | None = None,
        external_course_id: str | None = None,
        external_url: str | None = None,
    ) -> LmsSyncLog:
        _authorize(actor)
        if operation not in REPORTABLE:
            raise ValidationError({"operation": _("Unknown operation.")})
        if status not in FINAL_STATUSES:
            raise ValidationError({"status": _("Unknown status.")})
        text = (message or "").strip()[:MESSAGE_MAX] or None
        with session_context().system("lms.callback"):
            if log_id is not None:
                log = LmsSyncLog.objects.filter(platform=platform, pk=log_id).first()
                if log is None:
                    raise ValidationError({"log_id": _("Unknown sync log entry.")})
                if log.status != SyncStatus.QUEUED:
                    raise ValidationError({"log_id": _("This step is already finished.")})
                if log.operation != operation:
                    raise ValidationError({"operation": _("The operation does not match the sync log entry.")})
                section_id = section_id or log.section_id
            else:
                if (
                    section_id is not None
                    and not LmsCourseLink.objects.filter(platform=platform, section_id=section_id).exists()
                ):
                    raise ValidationError({"section_id": _("The section is not linked to this platform.")})
                log = LmsSyncLog.objects.create(
                    platform=platform,
                    section_id=section_id,
                    operation=operation,
                    status=SyncStatus.QUEUED,
                    payload={"reported_by": "platform"},
                    started_at=timezone.now(),
                )
            self.log.finish(log, SyncStatus(status), text)
            if operation == SyncOperation.COURSE_SYNC and section_id is not None:
                self._update_link(platform, section_id, status, text, external_course_id, external_url)
        return log

    @staticmethod
    def _update_link(
        platform: LmsPlatform,
        section_id: int,
        status: str,
        message: str | None,
        external_course_id: str | None,
        external_url: str | None,
    ) -> None:
        link = LmsCourseLink.objects.filter(platform=platform, section_id=section_id).first()
        if link is None:
            return
        if status == SyncStatus.SUCCEEDED:
            if external_course_id:
                link.external_course_id = external_course_id[:128]
            if external_url:
                link.external_url = external_url[:512]
            if link.external_course_id:
                link.status = LinkStatus.LINKED
                link.last_synced_at = timezone.now()
                link.last_error = None
        elif status == SyncStatus.FAILED:
            link.status = LinkStatus.FAILED
            link.last_error = message
        link.save()

    def deliver_scores(
        self, platform: LmsPlatform, actor: Any, *, external_course_id: str, scores: dict[str, Any]
    ) -> dict[str, Any]:
        """Returns the section, how many scores were delivered and how many map to an enrolled
        student with a user link."""
        _authorize(actor)
        if not isinstance(scores, dict) or len(scores) > MAX_SCORES:
            raise ValidationError({"scores": _("Send an object of user id to score.")})
        cleaned = {str(external): _score(value) for external, value in scores.items()}
        with session_context().system("lms.callback"):
            link = LmsCourseLink.objects.filter(platform=platform, external_course_id=external_course_id).first()
            if link is None:
                raise ValidationError({"external_course_id": _("No section is linked to this course.")})
            users = dict(
                LmsUserLink.objects.filter(platform=platform, external_user_id__in=list(cleaned)).values_list(
                    "user_id", "external_user_id"
                )
            )
            matched = 0
            for enrollment in enrolled(link.section_id):
                user = account_of(enrollment.student_record.person)
                if user is not None and users.get(user.pk) in cleaned:
                    matched += 1
            payload = {"external_course_id": external_course_id, "scores": cleaned, "matched": matched}
            self.log.run(
                platform,
                SyncOperation.GRADES_DELIVERED,
                {"section_id": link.section_id, "payload": payload},
                lambda: payload,
            )
        return {"section_id": link.section_id, "scores": len(cleaned), "matched": matched}
