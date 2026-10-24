"""Course CSV import (original ``App\\Filament\\Admin\\Imports\\CourseImporter``), registered in
``ninefruits.importing.registry`` as ``courses`` (admin screen and ``reference_import courses``)."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from django.core.exceptions import ValidationError
from django.utils.translation import gettext, pgettext_lazy

from ninefruits.curriculum.enums import GradingBasis
from ninefruits.curriculum.models import Course, CourseCategory, CourseVersion
from ninefruits.importing.resources import Column, ReferenceResource, RowImportFailed, translatable_columns


def _code(row: Mapping[str, Any], column: str = "code") -> str:
    return str(row.get(column) or "").strip()


def _fill_category(resource: ReferenceResource, version: Any, value: Any) -> None:
    if value is None:
        return
    category_id = CourseCategory.objects.filter(code=value).values_list("pk", flat=True).first()
    if category_id is None:
        raise RowImportFailed(gettext("The selected %(attribute)s is invalid.") % {"attribute": "category"})
    version.category_id = category_id


def _fill_grading_basis(resource: ReferenceResource, version: Any, value: Any) -> None:
    if value is not None:
        version.grading_basis = GradingBasis(value)


def _is_new(version: Any) -> bool:
    return bool(version._state.adding)


class CourseResource(ReferenceResource):
    """One row per course version. The course is found (or created) by code; the version by
    code and effective_start_date, so importing a revision adds a version and importing the same
    file again updates. Overlapping periods fail the row (exclusion constraint).

    Columns: code, org_unit (code, for new courses), effective_start_date, effective_end_date,
    title_{language}, credits, lecture_hours, lab_hours, category (code), grading_basis,
    counts_toward_credit_limit."""

    type_key = "courses"
    label = pgettext_lazy("curriculum", "courses")

    class Meta(ReferenceResource.Meta):
        model = CourseVersion

    @classmethod
    def columns(cls) -> list[Column]:
        return [
            Column("code", None, required_mapping=True, required=True, max_length=32, fill=lambda *args: None),
            Column("org_unit", None, fill=lambda *args: None),
            Column("effective_start_date", "effective_start_date", required_mapping=True, required=True, kind="date"),
            Column("effective_end_date", "effective_end_date", kind="date", after_or_equal="effective_start_date"),
            *translatable_columns("title"),
            Column("credits", "credits", required=_is_new, kind="numeric", minimum=0, maximum=30),
            Column("lecture_hours", "lecture_hours", kind="numeric", minimum=0, maximum=40),
            Column("lab_hours", "lab_hours", kind="numeric", minimum=0, maximum=40),
            Column("category", None, fill=_fill_category),
            Column("grading_basis", None, choices=GradingBasis, fill=_fill_grading_basis),
            Column("counts_toward_credit_limit", "counts_toward_credit_limit", kind="boolean"),
        ]

    def resolve_record(self, row: Mapping[str, Any]) -> CourseVersion:
        course = Course.objects.filter(code=_code(row)).first()
        start = _code(row, "effective_start_date")[:10]
        if course is None:
            # New course: created in before_save_instance(), inside the row's savepoint.
            return CourseVersion()
        existing = None
        if start:
            try:
                existing = CourseVersion.objects.filter(course=course, effective_start_date=start).first()
            except ValidationError:  # an unreadable date is reported by the column validation
                existing = None
        return existing or CourseVersion(course=course)

    def before_save_instance(self, instance: Any, row: Any, **kwargs: Any) -> None:
        if instance.course_id is not None:
            return
        from ninefruits.organization.models import OrgUnit

        unit = OrgUnit.objects.filter(code=_code(row, "org_unit")).first() if _code(row, "org_unit") else None
        if unit is None:
            raise RowImportFailed(gettext("New courses need an org_unit (code of the managing unit)."))
        instance.course = Course.objects.create(code=_code(row), org_unit=unit)
