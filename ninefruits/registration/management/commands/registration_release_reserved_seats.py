"""Hands reserved seats past their release time to the waitlists (original
``registration:release-reserved-seats``, scheduled every 5 minutes). Not audited as a command
(it runs every 5 minutes); the promotions it triggers are in the registration attempt log."""

from __future__ import annotations

from typing import Any

from ninefruits.core.commands import StatusCommand
from ninefruits.core.db import session_context
from ninefruits.registration.actions import ReleaseReservedSeats


class Command(StatusCommand):
    help = "Hand reserved seats past their release time to the waitlists (scheduled every 5 minutes)"

    def handle(self, *args: Any, **options: Any) -> int:  # type: ignore[override]  # exit code (StatusCommand)
        with session_context().system("command:registration_release_reserved_seats"):
            sections = ReleaseReservedSeats().handle()
        self.info(f"{len(sections)} section(s) with released seats.")
        return self.SUCCESS
