"""Courses with dated versions, requisites and equivalencies (original Filament
``Resources/Curriculum/Courses`` with ``VersionsRelationManager`` and
``EquivalenciesRelationManager``).

- The course page holds the identity (code, managing unit) with tabs for versions and equivalent
  courses. A version opens on its own page with its requisites.
- "Revise from a date" is the normal way to change a course: it ends the current version and
  starts a new one, so earlier sections keep their version (``ReviseCourse``).
- Version periods never overlap (database exclusion constraint); the forms explain an overlap
  before saving."""

from __future__ import annotations

from datetime import date
from typing import Any, ClassVar

from django import forms
from django.contrib import admin, messages
from django.core import validators
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import IntegrityError
from django.db.models import Count, Q
from django.http import HttpRequest, HttpResponse, HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.urls import path, reverse
from django.utils import timezone
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _
from django.utils.translation import pgettext_lazy
from unfold.admin import TabularInline
from unfold.decorators import display
from unfold.widgets import UnfoldAdminDateWidget, UnfoldAdminTextareaWidget

from ninefruits.adminpanel.mixins import CatalogPermissionMixin
from ninefruits.adminpanel.navigation import NavigationGroup
from ninefruits.curriculum.actions import CreateCourse, ReviseCourse
from ninefruits.curriculum.models import Course, CourseCategory, CourseEquivalency, CourseRequisite, CourseVersion
from ninefruits.i18n.fields import I18nSearchText
from ninefruits.institution.admin_support import ReferenceAdmin, admin_url, render_action_form
from ninefruits.organization.models import OrgUnit
from ninefruits.security.enums import Permission

COURSE_PERMISSIONS: dict[str, str] = {
    "view": Permission.REFERENCE_DATA_VIEW,
    "add": Permission.COURSES_MANAGE,
    "change": Permission.COURSES_MANAGE,
    "delete": Permission.COURSES_MANAGE,
}

VERSION_FIELDS = (
    "effective_start_date",
    "effective_end_date",
    "title",
    "description",
    "credits",
    "lecture_hours",
    "lab_hours",
    "category",
    "grading_basis",
    "counts_toward_credit_limit",
    "is_repeatable",
    "requires_evaluation",
)


def course_search(term: str, limit: int = 30) -> list[tuple[int, str]]:
    """Course options by code or current title (original ``CourseResource::courseSearch``)."""
    versions = (
        CourseVersion.objects.effective_on(timezone.localdate())
        .select_related("course")
        .annotate(_search=I18nSearchText("title"))
        .filter(Q(course__code__istartswith=term) | Q(_search__icontains=term))
        .order_by("course__code")[:limit]
    )
    return [(version.course_id, f"{version.course.code} {version.title}") for version in versions]


def overlaps(course_id: int | None, start: date | None, end: date | None, exclude_pk: Any = None) -> bool:
    """Whether another version of the course overlaps ``[start, end]`` (the exclusion constraint
    decides; this explains before saving)."""
    if course_id is None or start is None:
        return False
    versions = CourseVersion.objects.filter(course_id=course_id).filter(
        Q(effective_end_date__isnull=True) | Q(effective_end_date__gte=start)
    )
    if end is not None:
        versions = versions.filter(effective_start_date__lte=end)
    if exclude_pk is not None:
        versions = versions.exclude(pk=exclude_pk)
    return versions.exists()


def _active_categories() -> Any:
    return CourseCategory.objects.filter(is_active=True).order_by("sort_order", "code")


class VersionFieldsMixin(forms.ModelForm):  # type: ignore[type-arg]
    """Validation of a version's fields (original ``CourseResource::versionFields``)."""

    course_id_for_overlap: int | None = None

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        if "category" in self.fields:
            self.fields["category"].queryset = _active_categories()  # type: ignore[attr-defined]
        for name, (minimum, maximum) in {"credits": (0, 30), "lecture_hours": (0, 40), "lab_hours": (0, 40)}.items():
            if name in self.fields:
                self.fields[name].min_value = minimum  # type: ignore[attr-defined]
                self.fields[name].max_value = maximum  # type: ignore[attr-defined]
                self.fields[name].validators.extend(
                    [validators.MinValueValidator(minimum), validators.MaxValueValidator(maximum)]
                )

    def clean(self) -> dict[str, Any]:
        cleaned = super().clean() or {}
        start, end = cleaned.get("effective_start_date"), cleaned.get("effective_end_date")
        if start and end and end < start:
            self.add_error(
                "effective_end_date",
                _("The %(attribute)s field must be a date after or equal to %(date)s.")
                % {"attribute": _("Valid until"), "date": _("Valid from")},
            )
        elif overlaps(self._course_id(), start, end, self.instance.pk):
            self.add_error("effective_start_date", _("This period overlaps another version of the course."))
        return cleaned

    def _course_id(self) -> int | None:
        return self.course_id_for_overlap or self.instance.course_id


# -- courses -------------------------------------------------------------------------------------
class CourseForm(forms.ModelForm):  # type: ignore[type-arg]
    class Meta:
        model = Course
        fields = ("code", "org_unit", "is_active")

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        if "org_unit" in self.fields:
            self.fields["org_unit"].queryset = OrgUnit.objects.order_by("code")  # type: ignore[attr-defined]

    def clean_code(self) -> str:
        code = str(self.cleaned_data["code"])
        if not all(char.isalnum() or char in "-_" for char in code):
            raise ValidationError(
                _("The %(attribute)s field must only contain letters, numbers, dashes, and underscores.")
                % {"attribute": _("Course code")}
            )
        return code


class CourseCreateForm(CourseForm):
    """A new course with its first version (original ``CreateCourse`` page)."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        version_form = FirstVersionForm(prefix=None)
        for name in VERSION_FIELDS:
            self.fields[name] = version_form.fields[name]
        self.fields["category"].queryset = _active_categories()  # type: ignore[attr-defined]
        self.fields["effective_start_date"].required = True

    def clean(self) -> dict[str, Any]:
        cleaned = super().clean() or {}
        start, end = cleaned.get("effective_start_date"), cleaned.get("effective_end_date")
        if start and end and end < start:
            self.add_error(
                "effective_end_date",
                _("The %(attribute)s field must be a date after or equal to %(date)s.")
                % {"attribute": _("Valid until"), "date": _("Valid from")},
            )
        return cleaned

    def version_values(self) -> dict[str, Any]:
        values = {name: self.cleaned_data.get(name) for name in VERSION_FIELDS}
        category = values.pop("category")
        values["course_category_id"] = category.pk if category else None
        return values


class FirstVersionForm(VersionFieldsMixin):
    class Meta:
        model = CourseVersion
        fields = VERSION_FIELDS


class CourseVersionInline(CatalogPermissionMixin, TabularInline):
    """Versions of the course (read here; each opens on its own page with its requisites)."""

    model = CourseVersion
    fk_name = "course"
    extra = 0
    tab = True
    can_delete = False
    show_change_link = True
    fields = (
        "effective_start_date",
        "effective_end_date",
        "title_column",
        "credits",
        "category",
        "grading_basis",
        "requisites_count",
        "revise_link",
    )
    readonly_fields = fields
    verbose_name = _("course version")
    verbose_name_plural = _("versions")
    permissions: ClassVar[dict[str, str]] = COURSE_PERMISSIONS

    def has_add_permission(self, request: HttpRequest, obj: Any = None) -> bool:
        return False

    def has_change_permission(self, request: HttpRequest, obj: Any = None) -> bool:
        return False

    def get_queryset(self, request: HttpRequest) -> Any:
        self._request = request
        return (
            super()
            .get_queryset(request)
            .select_related("category")
            .annotate(requisite_total=Count("requisites"))
            .order_by("-effective_start_date")
        )

    @display(description=pgettext_lazy("curriculum", "Title"))
    def title_column(self, obj: CourseVersion) -> str:
        return str(obj.title or "")

    @display(description=_("Requisites"))
    def requisites_count(self, obj: CourseVersion) -> int:
        return int(getattr(obj, "requisite_total", 0) or 0)

    @admin.display(description="")
    def revise_link(self, obj: CourseVersion) -> str:
        request = getattr(self, "_request", None)
        if obj.pk is None or obj.effective_end_date is not None or request is None:
            return ""
        if not request.user.has_perm(Permission.COURSES_MANAGE):
            return ""
        url = reverse("admin:curriculum_course_revise", args=[obj.course_id, obj.pk])
        return format_html('<a href="{}" class="text-primary-600 underline">{}</a>', url, _("Revise from a date"))


class EquivalencyForm(forms.ModelForm):  # type: ignore[type-arg]
    class Meta:
        model = CourseEquivalency
        fields = ("equivalent_course", "is_mutual", "effective_start_date", "effective_end_date", "note")

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        if "equivalent_course" in self.fields:
            courses = Course.objects.order_by("code")
            if self.instance.course_id:
                courses = courses.exclude(pk=self.instance.course_id)
            self.fields["equivalent_course"].queryset = courses  # type: ignore[attr-defined]
            self.fields["equivalent_course"].label_from_instance = lambda course: course.code  # type: ignore[attr-defined]

    def clean(self) -> dict[str, Any]:
        cleaned = super().clean() or {}
        start, end = cleaned.get("effective_start_date"), cleaned.get("effective_end_date")
        if start and end and end < start:
            self.add_error(
                "effective_end_date",
                _("The %(attribute)s field must be a date after or equal to %(date)s.")
                % {"attribute": _("Valid until"), "date": _("Valid from")},
            )
        return cleaned


class CourseEquivalencyInline(CatalogPermissionMixin, TabularInline):
    """Substitutions: which course counts for this one, and in which period."""

    model = CourseEquivalency
    fk_name = "course"
    form = EquivalencyForm
    extra = 0
    tab = True
    verbose_name = _("equivalency")
    verbose_name_plural = _("equivalent courses")
    permissions: ClassVar[dict[str, str]] = COURSE_PERMISSIONS

    def has_add_permission(self, request: HttpRequest, obj: Any = None) -> bool:
        return self._allowed(request, "add")

    def get_queryset(self, request: HttpRequest) -> Any:
        return super().get_queryset(request).select_related("equivalent_course")


class ManagingUnitFilter(admin.SimpleListFilter):
    title = _("Managing unit")
    parameter_name = "org_unit"

    def lookups(self, request: HttpRequest, model_admin: Any) -> list[tuple[Any, Any]]:
        units = OrgUnit.objects.filter(pk__in=Course.objects.values("org_unit_id")).order_by("code")
        return [(unit.pk, str(unit)) for unit in units]

    def queryset(self, request: HttpRequest, queryset: Any) -> Any:
        return queryset.filter(org_unit_id=self.value()) if self.value() else queryset


class ReviseForm(VersionFieldsMixin):
    effective_from = forms.DateField(label=_("New version from"), widget=UnfoldAdminDateWidget)
    reason = forms.CharField(
        label=pgettext_lazy("common", "Reason"),
        max_length=1000,
        required=False,
        widget=UnfoldAdminTextareaWidget(attrs={"rows": 3}),
    )

    class Meta:
        model = CourseVersion
        fields = VERSION_FIELDS[2:]

    def __init__(self, *args: Any, current: CourseVersion, **kwargs: Any) -> None:
        self.current = current
        super().__init__(*args, instance=CourseVersion(course=current.course), **kwargs)
        # Fill the new version with the current one's values.
        for name in VERSION_FIELDS[2:]:
            self.initial[name] = getattr(current, "category_id" if name == "category" else name)
        self.initial["title"] = current.title_translations
        self.initial["description"] = current.description_translations
        self.order_fields(["effective_from", *VERSION_FIELDS[2:], "reason"])

    def clean(self) -> dict[str, Any]:
        cleaned = forms.ModelForm.clean(self) or {}
        start = cleaned.get("effective_from")
        if start and start <= self.current.effective_start_date:
            self.add_error(
                "effective_from",
                _("The %(attribute)s field must be a date after %(date)s.")
                % {"attribute": _("New version from"), "date": self.current.effective_start_date.isoformat()},
            )
        return cleaned

    def _post_clean(self) -> None:
        """The new version is built by ReviseCourse, not by this form."""

    def attributes(self) -> dict[str, Any]:
        values = {name: self.cleaned_data.get(name) for name in VERSION_FIELDS[2:]}
        category = values.pop("category")
        values["course_category_id"] = category.pk if category else None
        return values


@admin.register(Course)
class CourseAdmin(ReferenceAdmin):
    """Courses (legacy SFOBJECT) with dated versions, requisites and equivalencies."""

    manage_permission = Permission.COURSES_MANAGE
    navigation_group = NavigationGroup.CURRICULUM
    navigation_icon = "menu_book"
    navigation_order = 10
    import_type = "courses"
    form = CourseForm
    list_display = ("code", "title_column", "credits_column", "org_unit_column", "is_active")
    list_filter = (ManagingUnitFilter, "is_active")
    list_select_related = ("org_unit",)
    search_fields = ("code",)
    translated_search_fields = ()
    ordering = ("code",)
    inlines = (CourseVersionInline, CourseEquivalencyInline)

    def get_form(self, request: HttpRequest, obj: Any = None, change: bool = False, **kwargs: Any) -> Any:
        if obj is None:
            kwargs["form"] = CourseCreateForm
            kwargs["fields"] = ("code", "org_unit", "is_active")
        return super().get_form(request, obj, change=change, **kwargs)

    def get_fieldsets(self, request: HttpRequest, obj: Any = None) -> Any:
        if obj is None:
            return (
                (pgettext_lazy("curriculum.sections", "Course"), {"fields": ("code", "org_unit", "is_active")}),
                (_("First version"), {"fields": VERSION_FIELDS}),
            )
        return ((None, {"fields": ("code", "org_unit", "is_active", "add_version_link")}),)

    def get_readonly_fields(self, request: HttpRequest, obj: Any = None) -> Any:
        return ("add_version_link",) if obj is not None else ()

    @display(description=_("versions"))
    def add_version_link(self, obj: Course) -> str:
        if obj.pk is None:
            return ""
        url = reverse("admin:curriculum_courseversion_add") + f"?course={obj.pk}"
        return format_html('<a href="{}" class="text-primary-600 underline">{}</a>', url, _("Add course version"))

    def get_inlines(self, request: HttpRequest, obj: Any) -> Any:
        return self.inlines if obj is not None else ()

    def get_search_results(self, request: HttpRequest, queryset: Any, search_term: str) -> tuple[Any, bool]:
        queryset, duplicates = super().get_search_results(request, queryset, search_term)
        term = search_term.strip()
        if term:
            matches = (
                CourseVersion.objects.annotate(_search=I18nSearchText("title"))
                .filter(_search__icontains=term)
                .values("course_id")
            )
            queryset = queryset | self.get_queryset(request).filter(pk__in=matches)
        return queryset, duplicates

    def save_model(self, request: HttpRequest, obj: Course, form: Any, change: bool) -> None:
        if change:
            super().save_model(request, obj, form, change)
            return
        created = CreateCourse()(
            {"code": obj.code, "org_unit_id": obj.org_unit_id, "is_active": obj.is_active},
            form.version_values(),
            request.user,
        )
        for field in created._meta.concrete_fields:
            setattr(obj, field.attname, getattr(created, field.attname))
        obj._state.adding = False

    def response_add(self, request: HttpRequest, obj: Course, post_url_continue: str | None = None) -> HttpResponse:
        if "_addanother" not in request.POST and "_popup" not in request.POST:
            return HttpResponseRedirect(admin_url(obj))
        return super().response_add(request, obj, post_url_continue)

    _versions: dict[int, CourseVersion] | None = None

    def _current(self, obj: Course) -> CourseVersion | None:
        cache = self._versions
        if cache is None:
            today = timezone.localdate()
            cache = {v.course_id: v for v in CourseVersion.objects.effective_on(today)}
            self._versions = cache
        return cache.get(obj.pk)

    def changelist_view(self, request: HttpRequest, extra_context: dict[str, Any] | None = None) -> Any:
        self._versions = None
        return super().changelist_view(request, extra_context)

    @display(description=pgettext_lazy("curriculum", "Title"))
    def title_column(self, obj: Course) -> str:
        version = self._current(obj)
        return str(version.title) if version else "-"

    @display(description=pgettext_lazy("curriculum", "Credits"))
    def credits_column(self, obj: Course) -> str:
        version = self._current(obj)
        return str(version.credits) if version else "-"

    @display(description=_("Managing unit"))
    def org_unit_column(self, obj: Course) -> str:
        return str(obj.org_unit.name or obj.org_unit.code)

    # -- extra pages ----------------------------------------------------------------------------
    def get_urls(self) -> list[Any]:
        return [
            path(
                "<int:course_id>/versions/<int:version_id>/revise/",
                self.admin_site.admin_view(self.revise_view),
                name="curriculum_course_revise",
            ),
            *super().get_urls(),
        ]

    def revise_view(self, request: HttpRequest, course_id: int, version_id: int) -> HttpResponse:
        if not request.user.has_perm(Permission.COURSES_MANAGE):
            raise PermissionDenied
        current = get_object_or_404(CourseVersion.objects.select_related("course"), pk=version_id, course_id=course_id)
        form = ReviseForm(request.POST or None, current=current)
        if request.method == "POST" and form.is_valid():
            try:
                ReviseCourse()(
                    current.course,
                    form.cleaned_data["effective_from"],
                    form.attributes(),
                    request.user,
                    form.cleaned_data.get("reason") or None,
                )
            except ValidationError as error:
                for message in error.messages:
                    form.add_error(None, message)
            except IntegrityError:
                form.add_error(None, _("This period overlaps another version of the course."))
            else:
                messages.success(request, _("New version created."))
                return HttpResponseRedirect(admin_url(current.course))
        return render_action_form(
            self,
            request,
            form,
            _("Revise from a date"),
            admin_url(current.course),
            subtitle=current.label(),
            description=_(
                "The current version ends the day before; the new version starts with a copy of it and its "
                "requisites. Sections already offered keep their version."
            ),
        )


# -- versions and requisites ----------------------------------------------------------------------
class RequisiteForm(forms.ModelForm):  # type: ignore[type-arg]
    class Meta:
        model = CourseRequisite
        fields = ("kind", "group_number", "required_course", "minimum_grade", "allows_concurrent")

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        if "required_course" in self.fields:
            self.fields["required_course"].queryset = Course.objects.order_by("code")  # type: ignore[attr-defined]
            self.fields["required_course"].label_from_instance = lambda course: course.code  # type: ignore[attr-defined]
        if "group_number" in self.fields:
            self.fields["group_number"].validators.extend(
                [validators.MinValueValidator(1), validators.MaxValueValidator(20)]
            )


class RequisiteInline(CatalogPermissionMixin, TabularInline):
    """Courses in the same group are alternatives (one of them is enough); every group must be met."""

    model = CourseRequisite
    fk_name = "course_version"
    form = RequisiteForm
    extra = 0
    verbose_name = _("Requisites")
    verbose_name_plural = _("Requisites")
    permissions: ClassVar[dict[str, str]] = COURSE_PERMISSIONS

    def has_add_permission(self, request: HttpRequest, obj: Any = None) -> bool:
        return self._allowed(request, "add")


class CourseVersionForm(VersionFieldsMixin):
    class Meta:
        model = CourseVersion
        fields = ("course", *VERSION_FIELDS)

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        if "course" in self.fields:
            self.fields["course"].queryset = Course.objects.order_by("code")  # type: ignore[attr-defined]
            self.fields["course"].label_from_instance = lambda course: course.code  # type: ignore[attr-defined]

    def _course_id(self) -> int | None:
        course = self.cleaned_data.get("course") if hasattr(self, "cleaned_data") else None
        course_id: int | None = course.pk if course is not None else self.instance.course_id
        return course_id


@admin.register(CourseVersion)
class CourseVersionAdmin(ReferenceAdmin):
    """A version with its requisites (original version form with the requisites repeater). Reached
    from the course page; not in the sidebar."""

    manage_permission = Permission.COURSES_MANAGE
    navigation_group = NavigationGroup.CURRICULUM
    navigation_hidden = True
    form = CourseVersionForm
    inlines = (RequisiteInline,)
    list_display = ("course", "effective_start_date", "effective_end_date", "credits")
    list_select_related = ("course",)
    search_fields = ("course__code",)
    translated_search_fields = ("title",)

    def get_readonly_fields(self, request: HttpRequest, obj: Any = None) -> Any:
        return ("course",) if obj is not None else ()

    def get_changeform_initial_data(self, request: HttpRequest) -> dict[str, Any]:
        initial = super().get_changeform_initial_data(request)
        if request.GET.get("course"):
            initial["course"] = request.GET["course"]
        return initial

    def _course_url(self, obj: CourseVersion) -> HttpResponse:
        return HttpResponseRedirect(admin_url(obj.course))

    def response_add(self, request: HttpRequest, obj: CourseVersion, post_url_continue: str | None = None) -> Any:
        if "_continue" in request.POST or "_addanother" in request.POST:
            return super().response_add(request, obj, post_url_continue)
        return self._course_url(obj)

    def response_change(self, request: HttpRequest, obj: CourseVersion) -> Any:
        if "_continue" in request.POST or "_addanother" in request.POST:
            return super().response_change(request, obj)
        return self._course_url(obj)

    def response_delete(self, request: HttpRequest, obj_display: str, obj_id: Any) -> HttpResponse:
        course_id = getattr(self, "_deleted_course_id", None)
        if course_id is not None:
            return HttpResponseRedirect(reverse("admin:curriculum_course_change", args=[course_id]))
        return super().response_delete(request, obj_display, obj_id)

    def delete_model(self, request: HttpRequest, obj: CourseVersion) -> None:
        self._deleted_course_id = obj.course_id
        super().delete_model(request, obj)
