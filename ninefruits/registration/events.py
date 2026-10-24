"""Registration events (original ``EnrollmentConfirmed``, ``EnrollmentDropped``). LMS listeners
come in Phase 12; the waitlist listener is in ``listeners.py``."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class EnrollmentConfirmed:
    """A student is enrolled in a section (registration, waitlist promotion, staff enrollment)."""

    enrollment: Any


@dataclass(frozen=True)
class EnrollmentDropped:
    """An enrollment ended before completion (dropped or withdrawn)."""

    enrollment: Any
