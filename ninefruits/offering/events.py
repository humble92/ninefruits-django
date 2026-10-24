"""Offering events (original ``App\\Domain\\Offering\\Events``), dispatched with
``ninefruits.core.events.dispatch``. The LMS integration (Phase 12) listens to them."""

from __future__ import annotations

from dataclasses import dataclass

from ninefruits.offering.models import Section


@dataclass(frozen=True)
class SectionPublished:
    """A section became published (porting-plan 12: the LMS course is created)."""

    section: Section
