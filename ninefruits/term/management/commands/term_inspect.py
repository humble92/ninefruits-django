"""Show the terms in session and the open business windows at a point in time (original
``term:inspect``, a ``TermResolver`` check)."""

from __future__ import annotations

import io
import json
from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from django.core.management.base import CommandParser
from django.utils import timezone
from rich.console import Console
from rich.table import Table

from ninefruits.core.commands import StatusCommand
from ninefruits.term.enums import TermWindowType
from ninefruits.term.services import TermResolver


def parse_moment(text: str) -> datetime | None:
    """ISO date and time, optionally followed by an IANA time zone (``2027-02-15 09:00
    Asia/Seoul``). Without an offset or zone the server time zone applies (UTC), as in the
    original."""
    text = text.strip()
    zone: ZoneInfo | None = None
    head, _, tail = text.rpartition(" ")
    if head and ("/" in tail or tail == "UTC"):
        try:
            zone = ZoneInfo(tail)
        except ValueError, ZoneInfoNotFoundError:
            return None
        text = head
    try:
        moment = datetime.fromisoformat(text)
    except ValueError:
        return None
    if timezone.is_naive(moment):
        moment = moment.replace(tzinfo=zone or timezone.get_default_timezone())
    return moment


class Command(StatusCommand):
    help = "Show the terms in session and the open business windows at a point in time (TermResolver check)"

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument(
            "--at",
            help='Point in time to check (default now), e.g. "2027-02-15 09:00" (UTC) or "2027-02-15 09:00 Asia/Seoul"',
        )

    def handle(self, *args: Any, **options: Any) -> int:  # type: ignore[override]  # exit code (StatusCommand)
        resolver = TermResolver()
        zone = resolver.zone()
        if options.get("at"):
            at = parse_moment(str(options["at"]))
            if at is None:
                self.error(f"Cannot read the time [{options['at']}].")
                return self.FAILURE
        else:
            at = timezone.now()

        self.detail("Time", f"{at.isoformat()} (institution date {resolver.local_date(at).isoformat()})")
        in_session = resolver.in_session(at)
        self.detail("In session", ", ".join(term.code for term in in_session) or "-")

        rows = []
        for window_type in TermWindowType:
            for window in resolver.open_windows(window_type, at):
                eligibility = window.eligibility
                rows.append(
                    [
                        window_type.value,
                        window.term.code,
                        window.session.code if window.session else "-",
                        str(window.name or ""),
                        "everyone" if eligibility.is_everyone() else json.dumps(eligibility.to_dict()),
                        f"{window.closes_at.astimezone(zone):%Y-%m-%d %H:%M} {resolver.timezone()}",
                    ]
                )

        self.stdout.write("")
        if not rows:
            self.info("No business window is open.")
            return self.SUCCESS
        table = Table("Window", "Term", "Session", "Name", "Eligibility", "Closes")
        for row in rows:
            table.add_row(*row)
        buffer = io.StringIO()
        Console(file=buffer, width=160, force_terminal=False, color_system=None).print(table)
        self.stdout.write(buffer.getvalue().rstrip("\n"))
        return self.SUCCESS
