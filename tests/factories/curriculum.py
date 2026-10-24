"""Factories for course categories (original ``Database\\Factories\\Curriculum\\CourseCategoryFactory``)."""

from __future__ import annotations

import factory

from ninefruits.curriculum.models import CourseCategory


class CourseCategoryFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = CourseCategory

    code = factory.Sequence(lambda n: f"CAT{n:03d}")
    name = factory.Sequence(lambda n: {"en": f"Category {n}"})
