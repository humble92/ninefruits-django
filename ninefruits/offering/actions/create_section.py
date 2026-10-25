from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from django.core.exceptions import PermissionDenied, ValidationError
from django.db import IntegrityError, transaction
from django.utils.translation import gettext as _

from ninefruits.audit.logger import audit
from ninefruits.curriculum.models import Course, CourseVersion
from ninefruits.offering.models import Section
from ninefruits.security.enums import Permission
from ninefruits.security.services.authorization import authorization
from ninefruits.term.models import TermSession

from ._support import is_unique_violation

#: Section attributes taken from the data of CreateSection and UpdateSection.
SECTION_FIELDS = (
    "section_code",
    "capacity",
    "waitlist_capacity",
    "evaluation_method",
    "eligibility",
    "exclusion",
    "instruction_language",
    "note",
)


def version_for(course: Course, session: TermSession) -> CourseVersion:
    """The course version in effect when the session starts."""
    version = course.version_on(session.start_date)
    if version is None:
        raise ValidationError(
            {
                "course_id": _("Course %(course)s has no version in effect on %(date)s.")
                % {"course": course.code, "date": session.start_date.isoformat()}
            }
        )
    return version


def section_code_taken() -> ValidationError:
    return ValidationError({"section_code": _("This section number is already used for the course in this term.")})


class CreateSection:
    """Offers a course in a term session. The course version is the one in effect when the
    session starts; the offering unit defaults to the course's unit."""

    def __call__(self, session: TermSession, course: Course, data: Mapping[str, Any], created_by: Any) -> Section:
        org_unit_id = int(data.get("org_unit_id") or course.org_unit_id)
        scope = authorization().scope_for(created_by, Permission.SECTIONS_MANAGE)
        if not scope.is_global and org_unit_id not in scope.org_unit_ids:
            raise PermissionDenied

        version = version_for(course, session)
        values = {key: data[key] for key in SECTION_FIELDS if key in data and data[key] is not None}
        try:
            with transaction.atomic():
                section = Section.objects.create(
                    **values,
                    term_id=session.term_id,
                    session=session,
                    course=course,
                    version=version,
                    org_unit_id=org_unit_id,
                )
        except IntegrityError as error:
            if is_unique_violation(error):
                raise section_code_taken() from error
            raise

        audit(
            "section.created",
            section,
            properties={"course": course.code, "term_session_id": session.pk},
            causer=created_by,
        )
        return section
