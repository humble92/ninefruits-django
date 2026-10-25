# unfold.admin: the admin classes are Django's ModelAdmin and inlines with unfold's extra
# options (only those this project reads or overrides are declared).

from collections.abc import Sequence
from typing import Any

from django.contrib import admin
from django.http import HttpRequest, HttpResponse

class ModelAdmin(admin.ModelAdmin[Any]):
    actions_list: Sequence[str | dict[str, Any]]
    actions_list_hide_default: bool
    actions_row: Sequence[str | dict[str, Any]]
    actions_detail: Sequence[str | dict[str, Any]]
    actions_detail_hide_default: bool
    actions_submit_line: Sequence[str | dict[str, Any]]
    list_fullwidth: bool
    list_filter_submit: bool
    warn_unsaved_form: bool
    def _changeform_view(
        self, request: HttpRequest, object_id: str | None, form_url: str, extra_context: dict[str, Any] | None
    ) -> HttpResponse: ...

class StackedInline(admin.StackedInline[Any, Any]):
    tab: bool
    collapsible: bool
    show_count: bool
    per_page: int | None

class TabularInline(admin.TabularInline[Any, Any]):
    tab: bool
    collapsible: bool
    show_count: bool
    per_page: int | None
