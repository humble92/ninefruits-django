"""Reserved seats become open seats by themselves at ``releases_at`` (``SeatAllocator``). This
runs after that time to hand the freed seats to the waitlists (original
``ReleaseReservedSeats``, scheduled every 5 minutes)."""

from __future__ import annotations

from datetime import datetime

from django.db import transaction
from django.utils import timezone

from ninefruits.offering.models import SectionSeatGroup


class ReleaseReservedSeats:
    def __call__(self, at: datetime | None = None) -> list[int]:
        return self.handle(at)

    def handle(self, at: datetime | None = None) -> list[int]:
        """Returns the sections whose waitlists get a promotion task."""
        from ninefruits.registration.tasks import promote_waitlist

        at = (at or timezone.now()).replace(microsecond=0)
        groups = list(
            SectionSeatGroup.objects.filter(
                release_processed_at__isnull=True, releases_at__isnull=False, releases_at__lte=at
            ).values_list("pk", "section_id")
        )
        sections = list(dict.fromkeys(section_id for _pk, section_id in groups))
        # Counter-like column: no updated_at, so the audit trigger ignores the change.
        SectionSeatGroup.objects.filter(pk__in=[pk for pk, _section in groups]).update(release_processed_at=at)
        for section_id in sections:
            transaction.on_commit(lambda section_id=section_id: promote_waitlist.delay(section_id))
        return sections
