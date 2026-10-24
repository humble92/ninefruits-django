from __future__ import annotations

from typing import Any

from django.core.exceptions import PermissionDenied, ValidationError
from django.utils.translation import gettext as _

from ninefruits.offering.enums import InstructorRole
from ninefruits.offering.models import Section, SectionInstructor
from ninefruits.offering.services import ScheduleConflicts


class AssignSectionInstructor:
    """Assigns an instructor to a section. Several instructors can share a section; an
    instructor already teaching at one of its meeting times is refused by the database."""

    def __init__(self, conflicts: ScheduleConflicts | None = None) -> None:
        self.conflicts = conflicts or ScheduleConflicts()

    def __call__(self, section: Section, instructor: Any, role: InstructorRole | str, user: Any) -> SectionInstructor:
        if not section.is_manageable_by(user):
            raise PermissionDenied
        if not instructor.is_current(section.session.start_date):
            raise ValidationError({"instructor_id": _("This instructor is not employed when the session starts.")})
        if SectionInstructor.objects.filter(section_id=section.pk, instructor_id=instructor.pk).exists():
            raise ValidationError({"instructor_id": _("This instructor is already assigned.")})
        return self.conflicts.guard(
            lambda: SectionInstructor.objects.create(section=section, instructor=instructor, role=InstructorRole(role)),
            "instructor_id",
        )
