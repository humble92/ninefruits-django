"""Seats of a section (original ``SeatAllocator``, porting-plan 10.7, ADR 0010).

Callers hold the section row lock (:meth:`SeatAllocator.lock`, ``SELECT ... FOR UPDATE`` inside
the transaction), so seat decisions of one section happen one at a time and briefly; the rules
are evaluated before, outside the lock. The counters also have CHECK constraints
(``enrolled_count <= capacity``) as the last line of defence.

Reserved seats: a seat group that has not reached ``releases_at`` keeps its unused seats for its
students. A student of the group takes a group seat while one is free, anyone else takes a
general seat (capacity minus taken seats minus unused reserved seats). After ``releases_at`` the
unused seats are general seats automatically."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from django.db import transaction
from django.db.models import F

from ninefruits.offering.models import Section, SectionSeatGroup

#: The seat a student takes when no seat group applies.
GENERAL = "general"


@dataclass(frozen=True)
class Availability:
    general: int
    reserved: int

    def is_full(self) -> bool:
        return self.general == 0 and self.reserved == 0


class SeatAllocator:
    def lock(self, section_id: int) -> Section:
        if not transaction.get_connection().in_atomic_block:
            raise RuntimeError("Seats are taken inside a transaction.")
        # FOR NO KEY UPDATE: seat takers still wait for each other, but rows that only reference
        # the section (registration attempts, LMS sync logs: foreign key checks take KEY SHARE)
        # are not blocked by another student's seat lock. The version comes with the row, so no
        # query runs for it while the lock is held; only the section row is locked.
        section: Section = (
            Section.objects.select_related("version").select_for_update(of=("self",), no_key=True).get(pk=section_id)
        )
        return section

    def _reserved_groups(self, section: Section, at: datetime) -> list[SectionSeatGroup]:
        groups = SectionSeatGroup.objects.filter(section_id=section.pk).order_by("sort_order", "id")
        return [group for group in groups if group.is_reserved_at(at)]

    def find(self, section: Section, record: Any, at: datetime) -> SectionSeatGroup | str | None:
        """The seat the student would take: a seat group, ``GENERAL``, or ``None`` when no seat is
        free for them."""
        reserved = self._reserved_groups(section, at)
        group = next(
            (g for g in reserved if g.enrolled_count < g.capacity and g.eligibility.matches(record)),
            None,
        )
        if group is not None:
            return group
        unused = sum(max(0, g.capacity - g.enrolled_count) for g in reserved)
        return GENERAL if section.capacity - section.enrolled_count - unused > 0 else None

    def take(self, section: Section, seat: SectionSeatGroup | str) -> None:
        """Counters only (no ``updated_at``): the audit trigger ignores counter-only updates."""
        Section.objects.filter(pk=section.pk).update(enrolled_count=F("enrolled_count") + 1)
        section.enrolled_count += 1
        if isinstance(seat, SectionSeatGroup):
            SectionSeatGroup.objects.filter(pk=seat.pk).update(enrolled_count=F("enrolled_count") + 1)
            seat.enrolled_count += 1

    def release(self, section: Section, enrollment: Any) -> None:
        Section.objects.filter(pk=section.pk, enrolled_count__gt=0).update(enrolled_count=F("enrolled_count") - 1)
        section.enrolled_count = max(0, section.enrolled_count - 1)
        if enrollment.seat_group_id is not None:
            SectionSeatGroup.objects.filter(pk=enrollment.seat_group_id, enrolled_count__gt=0).update(
                enrolled_count=F("enrolled_count") - 1
            )

    def availability(
        self, section: Section, at: datetime, groups: list[SectionSeatGroup] | None = None
    ) -> Availability:
        """Free seats for display: general seats and unused reserved seats. ``groups``: the
        section's seat groups when the caller already loaded them."""
        if groups is None:
            reserved_groups = self._reserved_groups(section, at)
        else:
            reserved_groups = [g for g in groups if g.is_reserved_at(at)]
        reserved = sum(max(0, g.capacity - g.enrolled_count) for g in reserved_groups)
        return Availability(max(0, section.capacity - section.enrolled_count - reserved), reserved)
