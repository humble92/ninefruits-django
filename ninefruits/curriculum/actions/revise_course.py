from __future__ import annotations

from collections.abc import Mapping
from datetime import date, timedelta
from typing import Any

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils.translation import gettext as _

from ninefruits.audit.logger import audit
from ninefruits.curriculum.models import Course, CourseRequisite, CourseVersion


class ReviseCourse:
    """A new version of a course from a date (e.g. credits change from 2027): the version in
    effect ends the day before and the new one starts with a copy of its data and requisites,
    overridden by the given attributes. Sections already offered keep their version."""

    ATTRIBUTES = CourseVersion.ATTRIBUTES

    def __call__(
        self,
        course: Course,
        effective_from: date,
        attributes: Mapping[str, Any],
        revised_by: Any,
        reason: str | None = None,
    ) -> CourseVersion:
        current = course.version_on(effective_from)
        if current is None:
            raise ValidationError({"effective_start_date": _("There is no version in effect on that date.")})
        if current.effective_start_date == effective_from:
            raise ValidationError(
                {"effective_start_date": _("A version already starts on that date. Edit it instead.")}
            )

        with transaction.atomic():
            previous_end = current.effective_end_date
            current.effective_end_date = effective_from - timedelta(days=1)
            current.save(update_fields=["effective_end_date", "updated_at"])

            values = current.copy_values()
            values.update({key: value for key, value in attributes.items() if key in self.ATTRIBUTES})
            version = CourseVersion(
                course=course,
                effective_start_date=effective_from,
                effective_end_date=previous_end,
                **values,
            )
            version.save()

            CourseRequisite.objects.bulk_create(
                CourseRequisite(
                    course_version=version,
                    kind=requisite.kind,
                    group_number=requisite.group_number,
                    required_course_id=requisite.required_course_id,
                    minimum_grade=requisite.minimum_grade,
                    allows_concurrent=requisite.allows_concurrent,
                )
                for requisite in current.requisites.all()
            )

            audit(
                "course.revised",
                version,
                reason=reason,
                properties={
                    "course": course.code,
                    "previous_version_id": current.pk,
                    "effective_from": effective_from.isoformat(),
                },
                causer=revised_by,
            )
        return version
