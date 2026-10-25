"""The reference data importers (original ``OrgUnitImporter``, ``ProgramImporter``,
``BuildingImporter``, ``RoomImporter`` and ``LookupValueImporter``)."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from django.utils.translation import gettext_lazy as _

from ninefruits.facility.models import Building, Room
from ninefruits.importing.resources import (
    Column,
    ReferenceResource,
    RowImportFailed,
    translatable_columns,
    unknown_code,
)
from ninefruits.institution.models import LookupType, LookupValue
from ninefruits.organization.enums import DegreeLevel
from ninefruits.organization.models import OrgUnit, OrgUnitType, Program


def _code(row: Mapping[str, Any], column: str = "code") -> str:
    return str(row.get(column) or "").strip()


class OrgUnitResource(ReferenceResource):
    """Columns: code, type (org unit type code), parent (parent code), name_{language},
    short_name_{language}, effective_start_date, effective_end_date, sort_order. Parents must
    appear before their children in the file."""

    type_key = "org_units"
    label = _("org units")

    class Meta(ReferenceResource.Meta):
        model = OrgUnit

    @classmethod
    def columns(cls) -> list[Column]:
        return [
            Column("code", "code", required_mapping=True, required=True, max_length=64),
            Column("type", "org_unit_type", required_mapping=True, required=True, relation=(OrgUnitType, "code")),
            Column("parent", "parent", relation=(OrgUnit, "code")),
            *translatable_columns("name"),
            *translatable_columns("short_name", required=False),
            Column("effective_start_date", "effective_start_date", required_mapping=True, required=True, kind="date"),
            Column("effective_end_date", "effective_end_date", kind="date", after_or_equal="effective_start_date"),
            Column("sort_order", "sort_order", kind="integer"),
        ]

    def resolve_record(self, row: Mapping[str, Any]) -> OrgUnit:
        return OrgUnit.objects.filter(code=_code(row)).first() or OrgUnit(code=_code(row))


class ProgramResource(ReferenceResource):
    """Columns: code, org_unit (code), degree_level, name_{language}, degree_title_{language},
    standard_duration_years, effective_start_date, effective_end_date, allows_second_major,
    allows_minor."""

    type_key = "programs"
    label = _("programs")

    class Meta(ReferenceResource.Meta):
        model = Program

    @classmethod
    def columns(cls) -> list[Column]:
        return [
            Column("code", "code", required_mapping=True, required=True, max_length=64),
            Column("org_unit", "org_unit", required_mapping=True, required=True, relation=(OrgUnit, "code")),
            Column("degree_level", "degree_level", required_mapping=True, required=True, choices=DegreeLevel),
            *translatable_columns("name"),
            *translatable_columns("degree_title", required=False),
            Column(
                "standard_duration_years",
                "standard_duration_years",
                kind="numeric",
                minimum=0.5,
                maximum=10,
            ),
            Column("effective_start_date", "effective_start_date", required_mapping=True, required=True, kind="date"),
            Column("effective_end_date", "effective_end_date", kind="date", after_or_equal="effective_start_date"),
            Column("allows_second_major", "allows_second_major", kind="boolean"),
            Column("allows_minor", "allows_minor", kind="boolean"),
        ]

    def resolve_record(self, row: Mapping[str, Any]) -> Program:
        return Program.objects.filter(code=_code(row)).first() or Program(code=_code(row))


class BuildingResource(ReferenceResource):
    """Columns: code, name_{language}, address, is_active."""

    type_key = "buildings"
    label = _("buildings")

    class Meta(ReferenceResource.Meta):
        model = Building

    @classmethod
    def columns(cls) -> list[Column]:
        return [
            Column("code", "code", required_mapping=True, required=True, max_length=32),
            *translatable_columns("name"),
            Column("address", "address", max_length=1000),
            Column("is_active", "is_active", kind="boolean"),
        ]

    def resolve_record(self, row: Mapping[str, Any]) -> Building:
        return Building.objects.filter(code=_code(row)).first() or Building(code=_code(row))


def _fill_room_type(resource: ReferenceResource, room: Any, value: Any) -> None:
    if value is None:
        return
    room_type = LookupValue.objects.of_type(Room.ROOM_TYPE_LOOKUP).filter(code=value).first()
    if room_type is None:
        raise RowImportFailed(unknown_code("room_type", value))
    room.room_type = room_type


class RoomResource(ReferenceResource):
    """Columns: building (code), code (room number), name_{language}, room_type (code of the
    room_type code list), org_unit (code), capacity, is_schedulable, is_active."""

    type_key = "rooms"
    label = _("rooms")

    class Meta(ReferenceResource.Meta):
        model = Room

    @classmethod
    def columns(cls) -> list[Column]:
        return [
            Column("building", None, required_mapping=True, required=True, fill=lambda *args: None),
            Column("code", "code", required_mapping=True, required=True, max_length=32),
            *translatable_columns("name", required=False),
            Column("room_type", None, fill=_fill_room_type),
            Column("org_unit", "org_unit", relation=(OrgUnit, "code")),
            Column("capacity", "capacity", kind="integer", minimum=0),
            Column("is_schedulable", "is_schedulable", kind="boolean"),
            Column("is_active", "is_active", kind="boolean"),
        ]

    def resolve_record(self, row: Mapping[str, Any]) -> Room:
        building = Building.objects.filter(code=_code(row, "building")).first()
        if building is None:
            raise RowImportFailed(unknown_code("building", _code(row, "building")))
        return Room.objects.filter(building=building, code=_code(row)).first() or Room(
            building=building, code=_code(row)
        )


class LookupValueResource(ReferenceResource):
    """Columns: type (code list code, e.g. ethnicity), code, name_{language}, sort_order,
    is_active."""

    type_key = "lookup_values"
    label = _("codes")

    class Meta(ReferenceResource.Meta):
        model = LookupValue

    @classmethod
    def columns(cls) -> list[Column]:
        return [
            Column("type", None, required_mapping=True, required=True, fill=lambda *args: None),
            Column("code", "code", required_mapping=True, required=True, max_length=64),
            *translatable_columns("name"),
            Column("sort_order", "sort_order", kind="integer"),
            Column("is_active", "is_active", kind="boolean"),
        ]

    def resolve_record(self, row: Mapping[str, Any]) -> LookupValue:
        lookup_type = LookupType.objects.filter(code=_code(row, "type")).first()
        if lookup_type is None:
            raise RowImportFailed(unknown_code("type", _code(row, "type")))
        return LookupValue.objects.filter(lookup_type=lookup_type, code=_code(row)).first() or LookupValue(
            lookup_type=lookup_type, code=_code(row)
        )
