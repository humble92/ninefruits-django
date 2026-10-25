"""Answers "which term?" per business question instead of a global current-term flag
(original ``App\\Domain\\Term\\Services\\TermResolver``, porting-plan 10.2, ADR 0006). Past term
grading, current instruction and next term registration can all be active at the same time.

Dates are judged in the institution time zone; window times are absolute (timestamptz). Windows
about courses belong to a term session; ask :meth:`TermResolver.is_open_in_session` with the
section's session for them."""

from __future__ import annotations

from datetime import date, datetime
from zoneinfo import ZoneInfo

from django.utils import timezone

from ninefruits.core.targeting import TargetSubject
from ninefruits.term.enums import OPEN_STATUSES, TermStatus, TermWindowType
from ninefruits.term.models import Term, TermSession, TermWindow


class TermResolver:
    def __init__(self, institution_timezone: str | None = None) -> None:
        self._timezone = institution_timezone

    def in_session(self, at: datetime | None = None) -> list[Term]:
        """Terms whose instruction period includes the institution's local date."""
        local = self.local_date(at)
        return list(
            Term.objects.exclude(status=TermStatus.ARCHIVED)
            .filter(start_date__lte=local, end_date__gte=local)
            .select_related("term_type", "academic_year")
            .order_by("start_date")
        )

    def open_windows(self, window_type: TermWindowType | str, at: datetime | None = None) -> list[TermWindow]:
        """Windows of the type open at the moment, for terms that are published (or grades
        closed). Planned and archived terms never have open windows."""
        return list(
            TermWindow.objects.select_related("term", "session")
            .filter(window_type=TermWindowType(window_type), term__status__in=OPEN_STATUSES)
            .open_at(at or timezone.now())
            .order_by("opens_at", "id")
        )

    def terms_open_for(
        self,
        window_type: TermWindowType | str,
        subject: TargetSubject | None = None,
        at: datetime | None = None,
    ) -> list[Term]:
        """Terms with an open window of the type. With a subject, only windows whose eligibility
        matches it, e.g. "terms this student can register for now"."""
        terms: dict[int, Term] = {}
        for window in self.open_windows(window_type, at):
            if subject is None or window.eligibility.matches(subject):
                terms.setdefault(window.term_id, window.term)
        return sorted(terms.values(), key=lambda term: term.start_date)

    def is_open_in_session(
        self,
        window_type: TermWindowType | str,
        session: TermSession,
        subject: TargetSubject | None = None,
        at: datetime | None = None,
    ) -> bool:
        """Whether a course window of the type is open for a session, e.g. "can this student
        still drop a course of the second-half session?"."""
        return any(
            window.session_id == session.pk and (subject is None or window.eligibility.matches(subject))
            for window in self.open_windows(window_type, at)
        )

    def next_window(
        self,
        window_type: TermWindowType | str,
        subject: TargetSubject | None = None,
        at: datetime | None = None,
    ) -> TermWindow | None:
        """The next window of the type that has not opened yet, for "registration opens on ..."
        messages."""
        windows = (
            TermWindow.objects.select_related("term")
            .filter(
                window_type=TermWindowType(window_type),
                opens_at__gt=at or timezone.now(),
                term__status__in=OPEN_STATUSES,
            )
            .order_by("opens_at", "id")
        )
        return next((window for window in windows if subject is None or window.eligibility.matches(subject)), None)

    def timezone(self) -> str:
        if self._timezone is None:
            from ninefruits.settings.groups.institution import InstitutionSettings

            self._timezone = InstitutionSettings.load().timezone
        return self._timezone

    def zone(self) -> ZoneInfo:
        return ZoneInfo(self.timezone())

    def local_date(self, at: datetime | None = None) -> date:
        return (at or timezone.now()).astimezone(self.zone()).date()
