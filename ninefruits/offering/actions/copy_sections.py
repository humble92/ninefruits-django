from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, field
from datetime import timedelta
from typing import Any

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils.translation import gettext as _

from ninefruits.audit.logger import audit
from ninefruits.offering.enums import SectionStatus
from ninefruits.offering.models import Section, SectionInstructor, SectionMeeting, SectionSeatGroup, Syllabus
from ninefruits.offering.services import ScheduleConflicts
from ninefruits.term.models import Term, TermSession


@dataclass
class SectionCopyReport:
    """What CopySections did (or would do, for a dry run)."""

    created: list[str] = field(default_factory=list)
    #: Section label -> reason
    skipped: dict[str, str] = field(default_factory=dict)
    #: Section label -> what was left out
    notes: dict[str, list[str]] = field(default_factory=dict)

    def add_created(self, label: str) -> None:
        self.created.append(label)

    def skip(self, label: str, reason: str) -> None:
        self.skipped[label] = reason

    def note(self, label: str, note: str) -> None:
        self.notes.setdefault(label, []).append(note)

    def summary(self) -> dict[str, int]:
        return {"created": len(self.created), "skipped": len(self.skipped), "with_notes": len(self.notes)}

    def lines(self) -> list[str]:
        return [
            *(f"{label}: {reason}" for label, reason in self.skipped.items()),
            *(f"{label}: {'; '.join(notes)}" for label, notes in self.notes.items()),
        ]


class _DryRun(Exception):
    pass


class CopySections:
    """Starts a term's offering from an earlier term (e.g. last fall into this fall): sections
    that were not cancelled, in the user's scope, as drafts with the course version of the new
    session, current instructors, meetings with their rooms, seat groups (release times shifted)
    and the syllabus as an unpublished draft.

    Sessions are matched by code (full term otherwise). A room or instructor that is now taken is
    left out and reported; the section is still copied. A dry run does the whole copy in a
    transaction and rolls it back, so its report is exact."""

    def __init__(self, conflicts: ScheduleConflicts | None = None) -> None:
        self.conflicts = conflicts or ScheduleConflicts()

    def __call__(
        self,
        source_term: Term,
        target_term: Term,
        user: Any,
        org_unit_ids: Iterable[int] | None = None,
        dry_run: bool = False,
    ) -> SectionCopyReport:
        if source_term.pk == target_term.pk:
            raise ValidationError({"to_term_id": _("Choose two different terms.")})

        report = SectionCopyReport()
        shift = timedelta(days=(target_term.start_date - source_term.start_date).days)
        target_sessions = {session.code: session for session in TermSession.objects.filter(term=target_term)}
        full_term = target_term.full_term_session()

        sections = (
            Section.objects.filter(term=source_term)
            .exclude(status=SectionStatus.CANCELLED)
            .manageable_by(user)
            .select_related("course", "session")
            .prefetch_related("instructor_assignments__instructor", "meetings", "seat_groups")
            .order_by("course_id", "section_code")
        )
        if org_unit_ids is not None:
            sections = sections.filter(org_unit_id__in=list(org_unit_ids))

        try:
            with transaction.atomic():
                for section in sections:
                    if not section.is_manageable_by(user):
                        continue
                    session = target_sessions.get(section.session.code, full_term)
                    self._copy(section, target_term, session, shift, report)
                if dry_run:
                    raise _DryRun
                audit(
                    "sections.copied",
                    target_term,
                    properties={"from_term": source_term.code, **report.summary()},
                    causer=user,
                )
        except _DryRun:
            pass
        return report

    def _copy(
        self, source: Section, target_term: Term, session: TermSession, shift: timedelta, report: SectionCopyReport
    ) -> None:
        label = source.label()
        if Section.objects.filter(
            term=target_term, course_id=source.course_id, section_code=source.section_code
        ).exists():
            report.skip(label, _("already offered in that term"))
            return
        version = source.course.version_on(session.start_date)
        if version is None:
            report.skip(label, _("no course version in effect at the session start"))
            return

        section = Section.objects.create(
            section_code=source.section_code,
            capacity=source.capacity,
            waitlist_capacity=source.waitlist_capacity,
            evaluation_method=source.evaluation_method,
            org_unit_id=source.org_unit_id,
            eligibility=source.eligibility,
            exclusion=source.exclusion,
            instruction_language=source.instruction_language,
            note=source.note_translations or None,
            term=target_term,
            session=session,
            course_id=source.course_id,
            version=version,
            copied_from_section=source,
        )
        report.add_created(label)

        for assignment in source.instructor_assignments.all():
            if not assignment.instructor.is_current(session.start_date):
                report.note(
                    label,
                    _("instructor %(instructor)s is no longer employed")
                    % {"instructor": assignment.instructor.employee_number},
                )
                continue
            SectionInstructor.objects.create(
                section=section, instructor_id=assignment.instructor_id, role=assignment.role
            )

        for meeting in source.meetings.all():
            self._copy_meeting(meeting, section, session, label, report)

        for group in source.seat_groups.all():
            SectionSeatGroup.objects.create(
                section=section,
                name=group.name_translations,
                capacity=group.capacity,
                eligibility=group.eligibility,
                releases_at=group.releases_at + shift if group.releases_at is not None else None,
                sort_order=group.sort_order,
            )

        syllabus = Syllabus.objects.filter(section_id=source.pk).first()
        if syllabus is not None:
            Syllabus.objects.create(section=section, language=syllabus.language, content=syllabus.content)

    def _copy_meeting(
        self, meeting: SectionMeeting, section: Section, session: TermSession, label: str, report: SectionCopyReport
    ) -> None:
        def attempt(room_id: int | None) -> SectionMeeting:
            return SectionMeeting.objects.create(
                section=section,
                weekday=meeting.weekday,
                start_time=meeting.start_time,
                end_time=meeting.end_time,
                room_id=room_id,
                start_date=session.start_date,
                end_date=session.end_date,
            )

        try:
            self.conflicts.guard(lambda: attempt(meeting.room_id))
            return
        except ValidationError as error:
            if meeting.room_id is None:
                report.note(label, error.messages[0])
                return
        try:
            self.conflicts.guard(lambda: attempt(None))
        except ValidationError as error:
            # Without a room it can only be an instructor conflict: drop the meeting.
            report.note(label, error.messages[0])
            return
        report.note(label, _("room taken at %(time)s, copied without a room") % {"time": meeting.time_label()})
