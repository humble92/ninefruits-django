"""Buildings and rooms in the admin panel (original Filament
``Resources/Reference/{Buildings,Rooms}``)."""

from __future__ import annotations

from typing import Any

from django import forms
from django.contrib import admin
from django.core.validators import MinValueValidator
from django.db.models import Count
from django.http import HttpRequest
from django.utils.translation import gettext_lazy as _
from django.utils.translation import pgettext_lazy
from unfold.decorators import display

from ninefruits.facility.models import Building, Room
from ninefruits.institution.admin_support import ReferenceAdmin
from ninefruits.institution.models import LookupValue
from ninefruits.organization.models import OrgUnit
from ninefruits.security.enums import Permission


@admin.register(Building)
class BuildingAdmin(ReferenceAdmin):
    manage_permission = Permission.FACILITIES_MANAGE
    import_type = "buildings"
    navigation_icon = "apartment"
    navigation_order = 30
    fields = ("code", "name", "address", "is_active")
    list_display = ("code", "name_column", "rooms_count", "is_active")
    search_fields = ("code",)
    ordering = ("code",)

    def get_queryset(self, request: HttpRequest) -> Any:
        return super().get_queryset(request).annotate(room_total=Count("rooms"))

    @display(description=pgettext_lazy("reference", "Name"))
    def name_column(self, obj: Building) -> str:
        return str(obj.name or "")

    @display(description=_("Rooms"), ordering="room_total")
    def rooms_count(self, obj: Building) -> int:
        return int(getattr(obj, "room_total", 0))


class RoomForm(forms.ModelForm):  # type: ignore[type-arg]
    class Meta:
        model = Room
        fields = (
            "building",
            "code",
            "name",
            "room_type",
            "org_unit",
            "capacity",
            "is_schedulable",
            "is_active",
            "note",
        )

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.fields["building"].queryset = Building.objects.order_by("code")  # type: ignore[attr-defined]
        self.fields["room_type"].queryset = (  # type: ignore[attr-defined]
            LookupValue.objects.of_type(Room.ROOM_TYPE_LOOKUP).filter(is_active=True).order_by("sort_order", "code")
        )
        self.fields["org_unit"].queryset = OrgUnit.objects.order_by("code")  # type: ignore[attr-defined]
        self.fields["capacity"].validators.append(MinValueValidator(0))


@admin.register(Room)
class RoomAdmin(ReferenceAdmin):
    manage_permission = Permission.FACILITIES_MANAGE
    import_type = "rooms"
    navigation_icon = "meeting_room"
    navigation_order = 31
    form = RoomForm
    list_display = (
        "building_column",
        "code",
        "name_column",
        "room_type_column",
        "capacity",
        "is_schedulable",
        "is_active",
    )
    list_filter = ("building", "is_active")
    list_select_related = ("building", "room_type")
    search_fields = ("code",)
    ordering = ("building__code", "code")

    @display(description=_("Building"), ordering="building__code")
    def building_column(self, obj: Room) -> str:
        return obj.building.code

    @display(description=pgettext_lazy("reference", "Name"))
    def name_column(self, obj: Room) -> str:
        return str(obj.name or "-")

    @display(description=_("Room type"))
    def room_type_column(self, obj: Room) -> str:
        return str(obj.room_type.name) if obj.room_type else "-"
