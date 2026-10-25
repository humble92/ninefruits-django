"""Factories for grade scales (original ``Database\\Factories\\Grading``)."""

from __future__ import annotations

from decimal import Decimal

import factory

from ninefruits.grading.models import GradeScale, GradeScaleItem


class GradeScaleFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = GradeScale

    code = factory.Sequence(lambda n: f"SCALE{n}")
    name = factory.Sequence(lambda n: {"en": f"Scale {n}"})
    max_grade_points = Decimal("4.50")


class GradeScaleItemFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = GradeScaleItem

    grade_scale = factory.SubFactory(GradeScaleFactory)
    code = factory.Sequence(lambda n: f"G{n}")
    grade_points = Decimal("4.00")
    min_percentage = Decimal("90")
    max_percentage = Decimal("100")
