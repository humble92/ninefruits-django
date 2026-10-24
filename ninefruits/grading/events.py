"""Grading events (original ``GradesFinalized``). LMS and other integrations listen to it
(porting-plan 12, Phase 12)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class GradesFinalized:
    """A section's grades were finalized."""

    section: Any
    enrollment_ids: list[int] = field(default_factory=list)


@dataclass(frozen=True)
class TermClosed:
    """Term close finished: records closed, standing and honors decided, the term moved to
    grades closed."""

    term: Any
    counts: dict[str, int] = field(default_factory=dict)
