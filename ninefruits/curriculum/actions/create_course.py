from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from django.db import transaction

from ninefruits.audit.logger import audit
from ninefruits.curriculum.models import Course, CourseVersion


class CreateCourse:
    """A new course with its first version (original ``CreateCourse``)."""

    COURSE_FIELDS = ("code", "org_unit_id", "is_active")

    def __call__(self, course: Mapping[str, Any], version: Mapping[str, Any], created_by: Any) -> Course:
        """``course``: code, org_unit_id, is_active. ``version``: effective dates and
        ``CourseVersion.ATTRIBUTES``."""
        allowed = ("effective_start_date", "effective_end_date", *CourseVersion.ATTRIBUTES)
        with transaction.atomic():
            created = Course.objects.create(**{key: course[key] for key in self.COURSE_FIELDS if key in course})
            CourseVersion.objects.create(
                course=created, **{key: value for key, value in version.items() if key in allowed}
            )
            audit("course.created", created, properties={"code": created.code}, causer=created_by)
        return created
