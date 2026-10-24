"""Course categories in the admin panel (original Filament ``Resources/Reference/CourseCategories``).
The rest of the curriculum screens arrive with Phase 4."""

from __future__ import annotations

from typing import Any

from django import forms
from django.contrib import admin
from django.utils.translation import gettext_lazy as _
from django.utils.translation import pgettext_lazy
from unfold.decorators import display

from ninefruits.adminpanel.navigation import NavigationGroup
from ninefruits.curriculum.models import CourseCategory
from ninefruits.institution.admin_support import ReferenceAdmin
from ninefruits.security.enums import Permission


class CourseCategoryForm(forms.ModelForm):  # type: ignore[type-arg]
    class Meta:
        model = CourseCategory
        fields = ("code", "name", "parent", "sort_order", "is_active")

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        parents = CourseCategory.objects.order_by("code")
        if self.instance.pk:
            parents = parents.exclude(pk=self.instance.pk)
        self.fields["parent"].queryset = parents  # type: ignore[attr-defined]


@admin.register(CourseCategory)
class CourseCategoryAdmin(ReferenceAdmin):
    manage_permission = Permission.COURSE_CATEGORIES_MANAGE
    navigation_group = NavigationGroup.REFERENCE_DATA
    navigation_icon = "sell"
    navigation_order = 60
    form = CourseCategoryForm
    list_display = ("code", "name_column", "parent_column", "sort_order", "is_active")
    list_select_related = ("parent",)
    search_fields = ("code",)
    ordering = ("sort_order", "code")

    @display(description=pgettext_lazy("reference", "Name"))
    def name_column(self, obj: CourseCategory) -> str:
        return str(obj.name or "")

    @display(description=_("Parent"))
    def parent_column(self, obj: CourseCategory) -> str:
        return str(obj.parent.name) if obj.parent else "-"
