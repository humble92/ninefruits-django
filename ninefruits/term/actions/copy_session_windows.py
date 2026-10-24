from __future__ import annotations

from datetime import datetime, time, timedelta
from typing import Any

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone
from django.utils.translation import gettext as _

from ninefruits.audit.logger import audit
from ninefruits.term.models import TermSession, TermWindow


class CopySessionWindows:
    """Starts a session's course windows from another session's (normally the full term),
    shifted to the target dates. A window that opens in the first half of the source session
    keeps its distance from the session start (add/drop, withdrawal); a later one keeps its
    distance from the session end (grade entry, evaluation). Staff adjust after."""

    def __call__(self, source: TermSession, target: TermSession, copied_by: Any) -> int:
        """Returns the number of windows created."""
        if source.pk == target.pk or source.term_id != target.term_id:
            raise ValidationError({"source": _("Choose another session of the same term.")})
        if target.windows.exists():
            raise ValidationError({"source": _("This session already has windows.")})

        # Day boundaries in the application time zone, like the original (Carbon startOfDay).
        zone = timezone.get_default_timezone()
        source_start = datetime.combine(source.start_date, time.min, tzinfo=zone)
        source_end = datetime.combine(source.end_date, time.min, tzinfo=zone)
        midpoint = source_start + (source_end - source_start) / 2
        start_shift = timedelta(days=(target.start_date - source.start_date).days)
        end_shift = timedelta(days=(target.end_date - source.end_date).days)

        with transaction.atomic():
            count = 0
            for window in source.windows.order_by("opens_at", "id"):
                shift = start_shift if window.opens_at < midpoint else end_shift
                TermWindow.objects.create(
                    term_id=target.term_id,
                    session=target,
                    window_type=window.window_type,
                    name=window.name_translations or None,
                    opens_at=window.opens_at + shift,
                    closes_at=window.closes_at + shift,
                    eligibility=window.eligibility,
                )
                count += 1
            audit(
                "term_session.windows_copied",
                target,
                properties={"source_session_id": source.pk, "windows": count},
                causer=copied_by,
            )
        return count
