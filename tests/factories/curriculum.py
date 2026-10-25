"""Factories for course categories, courses, versions and requirement sets (original
``Database\\Factories\\Curriculum``)."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Any

import factory

from ninefruits.curriculum.enums import ProgramRole
from ninefruits.curriculum.models import Course, CourseCategory, CourseVersion, CurriculumRequirementSet
from tests.factories.organization import OrgUnitFactory, ProgramFactory


class CourseCategoryFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = CourseCategory

    code = factory.Sequence(lambda n: f"CAT{n:03d}")
    name = factory.Sequence(lambda n: {"en": f"Category {n}"})


class CourseFactory(factory.django.DjangoModelFactory):
    """Courses with one open-ended version from 2000 (original ``CourseFactory``).
    ``CourseFactory(version={...})`` replaces the default version (original ``withVersion``);
    ``CourseFactory(version=False)`` creates none."""

    class Meta:
        model = Course
        skip_postgeneration_save = True

    code = factory.Sequence(lambda n: f"TST{1000 + n}")
    org_unit = factory.SubFactory(OrgUnitFactory)

    @factory.post_generation
    def version(self, create: bool, extracted: Any, **kwargs: Any) -> None:
        if not create or extracted is False:
            return
        attributes = {**(extracted or {}), **kwargs}
        CourseVersionFactory(course=self, **attributes)


class CourseVersionFactory(factory.django.DjangoModelFactory):
    """``CourseVersionFactory(course=..., effective_start_date=..., effective_end_date=...)``
    (original ``between($start, $end)``)."""

    class Meta:
        model = CourseVersion

    course = factory.SubFactory(CourseFactory, version=False)
    effective_start_date = date(2000, 3, 1)
    effective_end_date = None
    title = factory.Sequence(lambda n: {"en": f"Introduction to Topic {n}"})
    credits = Decimal("3")
    lecture_hours = Decimal("3")


class CurriculumRequirementSetFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = CurriculumRequirementSet

    program = factory.SubFactory(ProgramFactory)
    program_role = ProgramRole.PRIMARY
    catalog_year_from = 2020
    name = {"en": "Requirements from 2020"}
    total_credits = Decimal("130")
