"""Countries, languages and code lists in the admin panel (original Filament
``Resources/Reference/{Countries,Languages,LookupTypes}``)."""

from __future__ import annotations

import re
from typing import Any, ClassVar

from django import forms
from django.contrib import admin
from django.core.exceptions import ValidationError
from django.db.models import Count
from django.http import HttpRequest
from django.utils.translation import gettext_lazy as _
from django.utils.translation import pgettext_lazy
from unfold.admin import TabularInline
from unfold.decorators import display

from ninefruits.adminpanel.mixins import CatalogPermissionMixin
from ninefruits.institution.admin_support import ReferenceAdmin
from ninefruits.institution.models import Country, Language, LookupType, LookupValue
from ninefruits.security.enums import Permission


class CountryForm(forms.ModelForm):  # type: ignore[type-arg]
    class Meta:
        model = Country
        fields = ("code", "alpha3_code", "numeric_code", "name", "is_active")

    def clean_code(self) -> str:
        return _exact_length(self.cleaned_data["code"], 2, _("ISO code"))

    def clean_alpha3_code(self) -> str:
        return _exact_length(self.cleaned_data["alpha3_code"], 3, _("Three-letter code"))

    def clean_numeric_code(self) -> str | None:
        value = self.cleaned_data.get("numeric_code") or None
        return None if value is None else _exact_length(value, 3, _("Numeric code"))


def _exact_length(value: str, length: int, label: Any) -> str:
    value = str(value).strip()
    if len(value) != length:
        raise ValidationError(
            _("The %(attribute)s field must be %(size)s characters.") % {"attribute": label, "size": length}
        )
    return value


@admin.register(Country)
class CountryAdmin(ReferenceAdmin):
    manage_permission = Permission.LOOKUP_VALUES_MANAGE
    navigation_icon = "public"
    navigation_order = 90
    form = CountryForm
    list_display = ("code", "alpha3_code", "name_column", "is_active")
    list_filter = ("is_active",)
    search_fields = ("code",)
    ordering = ("code",)

    @display(description=pgettext_lazy("reference", "Name"))
    def name_column(self, obj: Country) -> str:
        return str(obj.name or "")


class LanguageForm(forms.ModelForm):  # type: ignore[type-arg]
    class Meta:
        model = Language
        fields = ("code", "alpha3_code", "name", "is_active")

    def clean_alpha3_code(self) -> str | None:
        value = self.cleaned_data.get("alpha3_code") or None
        return None if value is None else _exact_length(value, 3, _("Three-letter code"))


@admin.register(Language)
class LanguageAdmin(ReferenceAdmin):
    manage_permission = Permission.LOOKUP_VALUES_MANAGE
    navigation_icon = "translate"
    navigation_order = 91
    form = LanguageForm
    list_display = ("code", "name_column", "is_active")
    list_filter = ("is_active",)
    search_fields = ("code",)
    ordering = ("code",)

    @display(description=pgettext_lazy("reference", "Name"))
    def name_column(self, obj: Language) -> str:
        return str(obj.name or "")


_CODE_PATTERN = re.compile(r"^[a-z][a-z0-9_]*$")


class LookupTypeForm(forms.ModelForm):  # type: ignore[type-arg]
    class Meta:
        model = LookupType
        fields = ("code", "name", "description")

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        # System lists are used by the application by code.
        self.fields["code"].disabled = bool(self.instance.pk and self.instance.is_system)

    def clean_code(self) -> str:
        code = str(self.cleaned_data["code"])
        if not self.fields["code"].disabled and not _CODE_PATTERN.match(code):
            raise ValidationError(_("The %(attribute)s field format is invalid.") % {"attribute": "code"})
        return code


class LookupValueInline(CatalogPermissionMixin, TabularInline):  # type: ignore[misc]
    """Original ``ValuesRelationManager``."""

    model = LookupValue
    fk_name = "lookup_type"
    extra = 0
    fields = ("code", "name", "sort_order", "is_active")
    verbose_name = _("code")
    verbose_name_plural = _("codes")
    permissions: ClassVar[dict[str, str]] = {
        "view": Permission.REFERENCE_DATA_VIEW,
        "add": Permission.LOOKUP_VALUES_MANAGE,
        "change": Permission.LOOKUP_VALUES_MANAGE,
        "delete": Permission.LOOKUP_VALUES_MANAGE,
    }

    def has_add_permission(self, request: HttpRequest, obj: Any = None) -> bool:
        return self._allowed(request, "add")


@admin.register(LookupType)
class LookupTypeAdmin(ReferenceAdmin):
    """Code data lists (legacy FNATION, FADMDIST, ROOM.FORWHAT ...). System lists are used by
    the application; their codes cannot change and they cannot be deleted."""

    manage_permission = Permission.LOOKUP_VALUES_MANAGE
    import_type = "lookup_values"
    navigation_icon = "list"
    navigation_order = 80
    form = LookupTypeForm
    list_display = ("code", "name_column", "values_count", "is_system")
    search_fields = ("code",)
    ordering = ("code",)
    inlines = (LookupValueInline,)

    def get_queryset(self, request: HttpRequest) -> Any:
        return super().get_queryset(request).annotate(value_total=Count("values"))

    def has_delete_permission(self, request: HttpRequest, obj: Any = None) -> bool:
        if obj is not None and obj.is_system:
            return False
        return super().has_delete_permission(request, obj)

    @display(description=pgettext_lazy("reference", "Name"))
    def name_column(self, obj: LookupType) -> str:
        return str(obj.name or "")

    @display(description=_("Codes"), ordering="value_total")
    def values_count(self, obj: LookupType) -> int:
        return int(getattr(obj, "value_total", 0))
