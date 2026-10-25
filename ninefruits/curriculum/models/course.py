"""Courses, their dated versions, requisites and equivalencies (original
``App\\Models\\Curriculum\\{Course,CourseVersion,CourseRequisite,CourseEquivalency}``, ADR 0009).

A course is an identity (legacy SFOBJECT code); everything that changes over time (title,
credits, category, requisites) is on its versions. Versions of one course never overlap
(exclusion constraint ``course_versions_no_overlap_excl``), so a date names exactly one version."""

from __future__ import annotations

from datetime import date
from typing import Any

from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.utils.translation import pgettext_lazy

from ninefruits.core.models import EffectivePeriodMixin, EffectiveQuerySet, TimeStampedModel, VisibleQuerySet
from ninefruits.curriculum.enums import GradingBasis, RequisiteKind
from ninefruits.i18n.fields import TranslatableJSONField

from .course_category import CourseCategory


class Course(TimeStampedModel):
    code = models.CharField(_("Course code"), max_length=32, unique=True)
    org_unit = models.ForeignKey(
        "organization.OrgUnit", on_delete=models.RESTRICT, related_name="courses", verbose_name=_("Managing unit")
    )
    is_active = models.BooleanField(pgettext_lazy("reference.fields", "Active"), default=True)

    objects = VisibleQuerySet.as_manager()

    class Meta:
        db_table = "courses"
        ordering = ["code"]
        verbose_name = _("course")
        verbose_name_plural = pgettext_lazy("curriculum", "courses")

    def __str__(self) -> str:
        version = self.version_on()
        return f"{self.code} {version.title}" if version is not None else self.code

    def version_on(self, on: date | str | None = None) -> CourseVersion | None:
        """The version in effect on the date (today by default)."""
        if isinstance(on, str):
            on = date.fromisoformat(on)
        return CourseVersion.objects.filter(course_id=self.pk).effective_on(on or timezone.localdate()).first()


class CourseVersion(EffectivePeriodMixin, TimeStampedModel):
    """A course as defined for a period. Sections record the version taught."""

    #: Attributes copied by a revision (original ``ReviseCourse::ATTRIBUTES``).
    ATTRIBUTES = (
        "title",
        "description",
        "credits",
        "lecture_hours",
        "lab_hours",
        "course_category_id",
        "grading_basis",
        "counts_toward_credit_limit",
        "is_repeatable",
        "requires_evaluation",
    )

    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name="versions")
    title = TranslatableJSONField(pgettext_lazy("curriculum", "Title"))
    title_translations: dict[str, str]  # TranslationsAccessor, set by the field
    description = TranslatableJSONField(
        pgettext_lazy("curriculum", "Description"), null=True, blank=True, max_length=2000
    )
    description_translations: dict[str, str]  # TranslationsAccessor, set by the field
    credits = models.DecimalField(pgettext_lazy("curriculum", "Credits"), max_digits=4, decimal_places=1)
    lecture_hours = models.DecimalField(_("Lecture hours"), max_digits=4, decimal_places=1, default=0)
    lab_hours = models.DecimalField(_("Lab hours"), max_digits=4, decimal_places=1, default=0)
    category = models.ForeignKey(
        CourseCategory,
        on_delete=models.RESTRICT,
        null=True,
        blank=True,
        db_column="course_category_id",
        related_name="course_versions",
        verbose_name=_("Course category"),
    )
    grading_basis = models.CharField(
        _("Grading"), max_length=16, choices=GradingBasis.choices, default=GradingBasis.GRADED
    )
    counts_toward_credit_limit = models.BooleanField(
        _("Counts toward the credit limit"),
        default=True,
        help_text=_("Turn off for courses outside the term credit limit (e.g. credit bank courses)."),
    )
    is_repeatable = models.BooleanField(
        _("May be taken again for credit"),
        default=False,
        help_text=_(
            "Taking it again earns credits again (e.g. seminars with changing topics) instead of being a retake."
        ),
    )
    requires_evaluation = models.BooleanField(
        pgettext_lazy("evaluation.fields", "Course evaluation"),
        default=True,
        help_text=_("Off for internships or practica that are not evaluated."),
    )

    objects = EffectiveQuerySet.as_manager()

    class Meta:
        db_table = "course_versions"
        ordering = ["course_id", "-effective_start_date"]
        verbose_name = _("course version")
        verbose_name_plural = _("versions")

    def __str__(self) -> str:
        return self.label()

    @property
    def course_category_id(self) -> int | None:
        return self.category_id

    @course_category_id.setter
    def course_category_id(self, value: int | None) -> None:
        self.category_id = value

    def label(self) -> str:
        """Label for lists and selects, e.g. "CSE2010 Data Structures (3.0)"."""
        return f"{self.course.code} {self.title or ''} ({self.credits})"

    def copy_values(self) -> dict[str, Any]:
        """The revisable attributes, translations as dicts."""
        values: dict[str, Any] = {name: getattr(self, name) for name in self.ATTRIBUTES}
        values["title"] = self.title_translations
        values["description"] = self.description_translations or None
        return values


class CourseRequisite(TimeStampedModel):
    """A requisite of a course version. Courses in one group are alternatives; all groups of a
    kind must be met. Registration checks them (Phase 5, with equivalent courses)."""

    course_version = models.ForeignKey(CourseVersion, on_delete=models.CASCADE, related_name="requisites")
    kind = models.CharField(pgettext_lazy("curriculum", "Kind"), max_length=16, choices=RequisiteKind.choices)
    group_number = models.SmallIntegerField(_("Group"), default=1)
    required_course = models.ForeignKey(
        Course,
        on_delete=models.RESTRICT,
        related_name="required_by",
        verbose_name=pgettext_lazy("curriculum.fields", "Course"),
    )
    minimum_grade = models.CharField(_("Minimum grade"), max_length=8, null=True, blank=True)
    allows_concurrent = models.BooleanField(_("May be taken in the same term"), default=False)

    objects = VisibleQuerySet.as_manager()

    class Meta:
        db_table = "course_requisites"
        ordering = ["kind", "group_number", "id"]
        verbose_name = _("Requisites")
        verbose_name_plural = _("Requisites")
        constraints = [
            models.UniqueConstraint(
                fields=["course_version", "kind", "group_number", "required_course"],
                name="course_requisites_course_version_id_kind_group_number_required_",
            ),
        ]

    def __str__(self) -> str:
        return f"{RequisiteKind(self.kind).label} {self.group_number}: {self.required_course.code}"


class CourseEquivalency(EffectivePeriodMixin, TimeStampedModel):
    """A substitution between courses for a period, e.g. after a curriculum reform the new course
    counts for the old one (and, if mutual, the other way round)."""

    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name="equivalencies")
    equivalent_course = models.ForeignKey(
        Course, on_delete=models.RESTRICT, related_name="equivalent_for", verbose_name=_("Equivalent course")
    )
    is_mutual = models.BooleanField(
        _("Mutual"),
        default=True,
        help_text=_("Each counts for the other. Off: only the equivalent course counts for this one."),
    )
    note = TranslatableJSONField(pgettext_lazy("curriculum", "Note"), null=True, blank=True)

    objects = EffectiveQuerySet.as_manager()

    class Meta:
        db_table = "course_equivalencies"
        ordering = ["effective_start_date", "id"]
        verbose_name = _("equivalency")
        verbose_name_plural = _("equivalent courses")

    def __str__(self) -> str:
        return f"{self.course.code} = {self.equivalent_course.code}"
