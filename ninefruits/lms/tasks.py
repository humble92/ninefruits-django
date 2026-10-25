"""LMS tasks (original ``SyncSectionJob``, ``SyncEnrollmentJob`` and the scheduled
``lms:reconcile``). They run as the system (``SystemTask``) and are retried three times: every
step is logged, and a platform error propagates so Celery tries again. Beat schedule in
``config/celery.py``: ``lms.reconcile`` daily at 02:30."""

from __future__ import annotations

from typing import Any

from celery import shared_task
from django.core.management import call_command

from ninefruits.core.tasks import SystemTask, single_instance

RETRIES = 3
RETRY_DELAY_SECONDS = 60


@shared_task(name="lms.sync_section", base=SystemTask, bind=True, max_retries=RETRIES)
def sync_section(self: Any, platform_id: int, section_id: int) -> dict[str, Any] | None:
    """Pushes one section to one platform (inactive or missing platforms are skipped)."""
    from ninefruits.lms.actions import SyncSection
    from ninefruits.lms.models import LmsPlatform
    from ninefruits.offering.models import Section

    platform = LmsPlatform.objects.filter(pk=platform_id, is_active=True).first()
    section = Section.objects.select_related("course").filter(pk=section_id).first()
    if platform is None or section is None:
        return None
    try:
        return dict(SyncSection().handle(platform, section))
    except Exception as error:
        if self.request.is_eager:
            raise
        raise self.retry(exc=error, countdown=RETRY_DELAY_SECONDS) from error


@shared_task(name="lms.sync_enrollment", base=SystemTask, bind=True, max_retries=RETRIES)
def sync_enrollment(self: Any, platform_id: int, enrollment_id: int, removed: bool = False) -> None:
    """Adds or removes one enrollment on one platform."""
    from ninefruits.lms.actions import SyncEnrollment
    from ninefruits.lms.models import LmsPlatform
    from ninefruits.registration.models import Enrollment

    platform = LmsPlatform.objects.filter(pk=platform_id, is_active=True).first()
    enrollment = (
        Enrollment.objects.select_related("section__course", "student_record__person__user")
        .filter(pk=enrollment_id)
        .first()
    )
    if platform is None or enrollment is None:
        return
    try:
        if removed:
            SyncEnrollment().removed(platform, enrollment)
        else:
            SyncEnrollment().added(platform, enrollment)
    except Exception as error:
        if self.request.is_eager:
            raise
        raise self.retry(exc=error, countdown=RETRY_DELAY_SECONDS) from error


@shared_task(name="lms.reconcile", base=SystemTask)
@single_instance("lms.reconcile")
def reconcile() -> Any:
    """Daily at 02:30 (original scheduled ``lms:reconcile``): every active platform. Runs the
    ``lms_reconcile`` command, so the scheduled run is audited like a manual one."""
    return call_command("lms_reconcile", verbosity=0)
