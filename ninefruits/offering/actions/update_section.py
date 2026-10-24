from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from django.apps import apps
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import IntegrityError
from django.utils.translation import gettext as _

from ninefruits.offering.models import Section
from ninefruits.offering.services import ScheduleConflicts
from ninefruits.term.models import TermSession

from ._support import is_unique_violation
from .create_section import SECTION_FIELDS, section_code_taken, version_for


def _has_entered_grades(section: Section) -> bool:
    """Enrollments with a grade (Phase 6). False until the registration app has them."""
    try:
        enrollment = apps.get_model("registration", "Enrollment")
    except LookupError:
        return False
    return bool(enrollment._default_manager.filter(section_id=section.pk).exclude(grade_status="none").exists())


class UpdateSection:
    """Edits a section. Moving it to another session of the term takes the course version of
    the new session start and moves meetings that followed the old session's dates."""

    def __init__(self, conflicts: ScheduleConflicts | None = None) -> None:
        self.conflicts = conflicts or ScheduleConflicts()

    def __call__(self, section: Section, data: Mapping[str, Any], updated_by: Any) -> Section:
        if not section.is_manageable_by(updated_by):
            raise PermissionDenied

        session_id = int(data.get("term_session_id") or section.session_id)

        def change() -> Section:
            if session_id != section.session_id:
                old = section.session
                new = TermSession.objects.filter(term_id=section.term_id, pk=session_id).first()
                if new is None:
                    raise ValidationError({"term_session_id": _("Choose a session of the section's term.")})
                section.session = new
                section.version = version_for(section.course, new)
                for meeting in section.meetings.all():
                    if meeting.start_date == old.start_date and meeting.end_date == old.end_date:
                        meeting.start_date = new.start_date
                        meeting.end_date = new.end_date
                        meeting.save(update_fields=["start_date", "end_date", "updated_at"])

            # Grades already entered follow the evaluation method they were entered under.
            method = data.get("evaluation_method")
            if method is not None and str(method) != section.evaluation_method and _has_entered_grades(section):
                raise ValidationError(
                    {"evaluation_method": _("Grades are already entered; the evaluation method cannot change.")}
                )

            # Registration takes seats under this row lock; capacity never drops below them.
            enrolled = (
                Section.objects.select_for_update().filter(pk=section.pk).values_list("enrolled_count", flat=True).get()
            )
            if data.get("capacity") is not None and int(data["capacity"]) < enrolled:
                raise ValidationError(
                    {
                        "capacity": _("Capacity cannot be below the %(count)s students already registered.")
                        % {"count": enrolled}
                    }
                )

            for key in (*SECTION_FIELDS, "org_unit_id"):
                if key in data:
                    setattr(section, key, data[key])
            section.save()
            return section

        try:
            return self.conflicts.guard(change, "term_session_id")
        except IntegrityError as error:
            if is_unique_violation(error):
                raise section_code_taken() from error
            raise
