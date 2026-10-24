"""Factories for buildings and rooms (original ``Database\\Factories\\Facility``)."""

from __future__ import annotations

import factory

from ninefruits.facility.models import Building, Room


class BuildingFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Building

    code = factory.Sequence(lambda n: f"B{n:03d}")
    name = factory.Sequence(lambda n: {"en": f"Hall {n}"})


class RoomFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Room

    building = factory.SubFactory(BuildingFactory)
    code = factory.Sequence(lambda n: f"{100 + n}")
    capacity = 40
