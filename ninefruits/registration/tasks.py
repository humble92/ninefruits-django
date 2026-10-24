"""Registration tasks (original ``PromoteWaitlistJob`` and the scheduled commands,
porting-plan 13.1). Beat schedule in ``config/celery.py``: ``registration.release_reserved_seats``
every 5 minutes, ``registration.promote_waitlists`` hourly."""

from __future__ import annotations

from typing import Any

from celery import shared_task
from django.core.cache import cache

from ninefruits.core.tasks import SystemTask, single_instance

#: Seconds a section's promotion lock lives at most (original ``uniqueFor``).
PROMOTION_LOCK_SECONDS = 60


def promotion_lock_key(section_id: int) -> str:
    return f"lock:registration.promote_waitlist:{section_id}"


@shared_task(name="registration.promote_waitlist", base=SystemTask, bind=True)
def promote_waitlist(self: Any, section_id: int) -> dict[str, int] | None:
    """Promotes a section's waitlist after a seat is freed. One run per section at a time (Redis
    lock): a run serves every free seat, so a concurrent request has nothing left to do; the
    hourly ``registration.promote_waitlists`` catches anything freed during a run."""
    from ninefruits.offering.models import Section
    from ninefruits.registration.actions import PromoteWaitlist

    key = promotion_lock_key(section_id)
    if not cache.add(key, "1", PROMOTION_LOCK_SECONDS):
        return None
    try:
        section = Section.objects.filter(pk=section_id).first()
        return PromoteWaitlist().handle(section) if section is not None else None
    finally:
        cache.delete(key)


@shared_task(name="registration.promote_waitlists", base=SystemTask)
@single_instance("registration.promote_waitlists")
def promote_waitlists() -> dict[str, int]:
    """Hourly safety net (original scheduled ``waitlist:promote``): serves every waitlist and
    expires those whose windows have closed."""
    from ninefruits.registration.services.waitlists import promote_all

    return promote_all()


@shared_task(name="registration.release_reserved_seats", base=SystemTask)
@single_instance("registration.release_reserved_seats", timeout=280)
def release_reserved_seats() -> list[int]:
    """Every 5 minutes (original scheduled ``registration:release-reserved-seats``)."""
    from ninefruits.registration.actions import ReleaseReservedSeats

    return ReleaseReservedSeats().handle()
