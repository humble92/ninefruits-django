"""Authorization entry points (porting-plan 7.2). Filled in by the security work of Phase 0."""

from __future__ import annotations

from typing import Any


def can_access_admin(user: Any) -> bool:
    return False
