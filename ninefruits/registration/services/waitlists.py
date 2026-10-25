"""Serving every waitlist at once (``waitlist_promote`` and the hourly task)."""

from __future__ import annotations

from typing import Any

from ninefruits.registration.enums import WaitlistStatus


def promote_all(term_id: int | None = None) -> dict[str, Any]:
    """Promotes waiting students of every section with a waitlist (of a term)."""
    from ninefruits.offering.models import Section
    from ninefruits.registration.actions import PromoteWaitlist
    from ninefruits.registration.models import WaitlistEntry

    sections = Section.objects.filter(
        pk__in=WaitlistEntry.objects.filter(status=WaitlistStatus.WAITING).values("section_id")
    ).order_by("pk")
    if term_id is not None:
        sections = sections.filter(term_id=term_id)
    totals: dict[str, Any] = {"sections": 0, "promoted": 0, "removed": 0, "expired": 0}
    promote = PromoteWaitlist()
    for section in sections:
        totals["sections"] += 1
        for key, count in promote.handle(section).items():
            totals[key] += count
    return totals


def waiting_counts(section_ids: list[int]) -> dict[int, int]:
    """Waiting entries per section. Counted as the system: row level security shows a student
    only their own entries, but the waitlist size and positions count everyone."""
    from django.db.models import Count

    from ninefruits.core.db import session_context
    from ninefruits.registration.models import WaitlistEntry

    with session_context().system("registration.waitlist_count"):
        rows = (
            WaitlistEntry.objects.filter(section_id__in=section_ids, status=WaitlistStatus.WAITING)
            .values("section_id")
            .annotate(count=Count("pk"))
        )
        return {row["section_id"]: row["count"] for row in rows}


def position(entry: Any) -> int:
    """Position among the waiting entries of the section (1 = next), counted as the system."""
    from ninefruits.core.db import session_context

    with session_context().system("registration.waitlist_count"):
        return int(entry.position())


def positions(entries: list[Any]) -> dict[int, int]:
    """:func:`position` of several entries (entry id -> position) with one query, for lists such
    as a student's waitlists on the registration page."""
    if not entries:
        return {}
    from ninefruits.core.db import session_context
    from ninefruits.registration.models import WaitlistEntry

    with session_context().system("registration.waitlist_count"):
        waiting = list(
            WaitlistEntry.objects.filter(
                section_id__in={entry.section_id for entry in entries}, status=WaitlistStatus.WAITING
            ).values_list("section_id", "requested_at")
        )
    return {
        entry.pk: sum(
            1
            for section_id, requested_at in waiting
            if section_id == entry.section_id and requested_at <= entry.requested_at
        )
        for entry in entries
    }
