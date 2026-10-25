"""Factories for org units and programs (original ``Database\\Factories\\Organization``)."""

from __future__ import annotations

from datetime import date

import factory

from ninefruits.organization.enums import DegreeLevel, OrgUnitChangeType
from ninefruits.organization.models import OrgUnit, OrgUnitSuccession, OrgUnitType, Program


class OrgUnitTypeFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = OrgUnitType

    code = factory.Sequence(lambda n: f"unittype{n}")
    name = factory.Sequence(lambda n: {"en": f"Unit type {n}"})


class OrgUnitFactory(factory.django.DjangoModelFactory):
    """``OrgUnitFactory(parent=college)`` (original ``under``), ``OrgUnitFactory(ended=date)``."""

    class Meta:
        model = OrgUnit

    code = factory.Sequence(lambda n: f"OU{n:04d}")
    name = factory.Sequence(lambda n: {"en": f"Department of Studies {n}"})
    org_unit_type = factory.SubFactory(OrgUnitTypeFactory)
    effective_start_date = date(2000, 3, 1)

    class Params:
        ended = None

    @factory.lazy_attribute
    def effective_end_date(self) -> date | None:
        return self.ended


class OrgUnitSuccessionFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = OrgUnitSuccession

    predecessor = factory.SubFactory(OrgUnitFactory)
    successor = factory.SubFactory(OrgUnitFactory)
    change_type = OrgUnitChangeType.RENAMED
    effective_date = date(2020, 3, 1)


class ProgramFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Program

    code = factory.Sequence(lambda n: f"P{n:05d}")
    name = factory.Sequence(lambda n: {"en": f"Bachelor of Studies {n}"})
    degree_level = DegreeLevel.BACHELOR
    org_unit = factory.SubFactory(OrgUnitFactory)
    standard_duration_years = 4
    effective_start_date = date(2000, 3, 1)
