# unfold.contrib.filters.admin: the list filters this project uses, on their Django bases.

from typing import Any

from django.contrib import admin

class DropdownFilter(admin.SimpleListFilter):
    all_option: list[Any]

class RadioFilter(admin.SimpleListFilter):
    all_option: list[Any]

class ChoicesDropdownFilter(admin.ChoicesFieldListFilter): ...
class RelatedDropdownFilter(admin.RelatedFieldListFilter): ...
class RangeDateTimeFilter(admin.FieldListFilter): ...
