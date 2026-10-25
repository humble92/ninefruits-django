"""Domain events -> synchronization tasks for every active platform (original ``QueueLmsSync``,
porting-plan 12). The listeners run after the surrounding transaction commits, so a rolled back
change sends nothing. Finalized grades are not pushed: the academic system is their source and
the LMS keeps its own raw scores; the listener is kept so every event the integration sees is
listed here."""

from __future__ import annotations

from ninefruits.core.events import listen
from ninefruits.grading.events import GradesFinalized
from ninefruits.offering.events import SectionPublished
from ninefruits.registration.events import EnrollmentConfirmed, EnrollmentDropped


def _platforms() -> list[tuple[int, bool]]:
    from ninefruits.lms.models import LmsPlatform

    return list(LmsPlatform.objects.active().order_by("pk").values_list("pk", "should_sync_enrollments"))


@listen(SectionPublished, after_commit=True)
def queue_section_sync(event: SectionPublished) -> None:
    from .tasks import sync_section

    for platform_id, _rosters in _platforms():
        sync_section.delay(platform_id, event.section.pk)


@listen(EnrollmentConfirmed, after_commit=True)
def queue_enrollment_added(event: EnrollmentConfirmed) -> None:
    from .tasks import sync_enrollment

    for platform_id, rosters in _platforms():
        if rosters:
            sync_enrollment.delay(platform_id, event.enrollment.pk)


@listen(EnrollmentDropped, after_commit=True)
def queue_enrollment_removed(event: EnrollmentDropped) -> None:
    from .tasks import sync_enrollment

    for platform_id, rosters in _platforms():
        if rosters:
            sync_enrollment.delay(platform_id, event.enrollment.pk, removed=True)


@listen(GradesFinalized)
def grades_finalized(event: GradesFinalized) -> None:
    """Nothing to push (ADR 0017: finalized grades stay in the academic system)."""
