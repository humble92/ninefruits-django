"""Graduation requirements (original ``App\\Models\\Curriculum\\{CurriculumRequirementSet,
CurriculumRequirement}`` and the ``curriculum_requirement_courses`` pivot, ADR 0009).

A set belongs to a program in a role (primary, second major, minor) for a range of catalog
years. Ranges of one program and role never overlap (``curriculum_requirement_sets_no_overlap_excl``
on the generated ``catalog_years`` int4range), so a student's catalog year names exactly one set.
The graduation audit (Phase 11) evaluates them."""

from __future__ import annotations

from typing import Self

from django.db import models
from django.db.models import Q
from django.utils.translation import gettext_lazy as _
from django.utils.translation import pgettext_lazy

from ninefruits.core.models import TimeStampedModel, VisibleQuerySet
from ninefruits.curriculum.enums import ProgramRole, RequirementKind
from ninefruits.i18n.fields import TranslatableJSONField

from .course import Course
from .course_category import CourseCategory


class CurriculumRequirementSetQuerySet(VisibleQuerySet):
    def for_catalog_year(self, catalog_year: int) -> Self:
        """Sets whose catalog years contain the year (``catalog_years @> year``)."""
        return self.filter(catalog_year_from__lte=catalog_year).filter(
            Q(catalog_year_to__isnull=True) | Q(catalog_year_to__gte=catalog_year)
        )

    def overlapping(self, year_from: int, year_to: int | None) -> Self:
        """Sets whose catalog years overlap ``[year_from, year_to]`` (open end when None)."""
        queryset = self.filter(Q(catalog_year_to__isnull=True) | Q(catalog_year_to__gte=year_from))
        return queryset if year_to is None else queryset.filter(catalog_year_from__lte=year_to)


class CurriculumRequirementSet(TimeStampedModel):
    program = models.ForeignKey(
        "organization.Program",
        on_delete=models.RESTRICT,
        related_name="requirement_sets",
        verbose_name=_("Programs"),
    )
    program_role = models.CharField(
        _("Program role"), max_length=16, choices=ProgramRole.choices, default=ProgramRole.PRIMARY
    )
    catalog_year_from = models.SmallIntegerField(_("Catalog year from"))
    catalog_year_to = models.SmallIntegerField(
        _("Catalog year to"),
        null=True,
        blank=True,
        help_text=_("Empty: also for later catalog years until another set starts."),
    )
    name = TranslatableJSONField(pgettext_lazy("reference", "Name"))
    total_credits = models.DecimalField(_("Total credits"), max_digits=5, decimal_places=1, null=True, blank=True)
    note = TranslatableJSONField(pgettext_lazy("curriculum", "Note"), null=True, blank=True, max_length=2000)

    objects = CurriculumRequirementSetQuerySet.as_manager()

    class Meta:
        db_table = "curriculum_requirement_sets"
        ordering = ["program__code", "program_role", "catalog_year_from"]
        verbose_name = _("graduation requirements")
        verbose_name_plural = _("graduation requirements")

    def __str__(self) -> str:
        return str(self.name or f"{self.program_role} {self.catalog_year_from}")

    @classmethod
    def applicable(cls, program_id: int, role: ProgramRole | str, catalog_year: int) -> CurriculumRequirementSet | None:
        """The set that applies to a program, role and catalog year."""
        return cls.objects.filter(program_id=program_id, program_role=str(role)).for_catalog_year(catalog_year).first()


class CurriculumRequirement(TimeStampedModel):
    """One line of a requirement set: credits in a category, required courses, a choice from a
    group of courses, or a passed examination."""

    requirement_set = models.ForeignKey(
        CurriculumRequirementSet,
        on_delete=models.CASCADE,
        related_name="requirements",
        db_column="curriculum_requirement_set_id",
    )
    kind = models.CharField(_("Requirement"), max_length=32, choices=RequirementKind.choices)
    name = TranslatableJSONField(pgettext_lazy("reference", "Name"), null=True, blank=True)
    category = models.ForeignKey(
        CourseCategory,
        on_delete=models.RESTRICT,
        null=True,
        blank=True,
        db_column="course_category_id",
        related_name="requirements",
        verbose_name=_("Course category"),
    )
    #: The kind to pass for ``assessment_pass`` requirements (Phase 9).
    assessment_type = models.ForeignKey(
        "assessment.AssessmentType",
        on_delete=models.RESTRICT,
        null=True,
        blank=True,
        related_name="requirements",
        verbose_name=_("Examination kind"),
    )
    min_credits = models.DecimalField(
        pgettext_lazy("curriculum", "Minimum credits"), max_digits=5, decimal_places=1, null=True, blank=True
    )
    min_courses = models.SmallIntegerField(_("Minimum courses"), null=True, blank=True)
    sort_order = models.IntegerField(_("Order"), default=0)
    courses = models.ManyToManyField(
        Course,
        through="CurriculumRequirementCourse",
        related_name="requirements",
        blank=True,
        verbose_name=pgettext_lazy("curriculum", "courses"),
    )

    objects = VisibleQuerySet.as_manager()

    class Meta:
        db_table = "curriculum_requirements"
        ordering = ["sort_order", "id"]
        verbose_name = _("Requirements")
        verbose_name_plural = _("Requirements")

    def __str__(self) -> str:
        return str(self.name or RequirementKind(self.kind).label)

    @property
    def curriculum_requirement_set_id(self) -> int:
        return int(self.requirement_set_id)


class CurriculumRequirementCourse(TimeStampedModel):
    requirement = models.ForeignKey(
        CurriculumRequirement, on_delete=models.CASCADE, db_column="curriculum_requirement_id", related_name="+"
    )
    course = models.ForeignKey(Course, on_delete=models.RESTRICT, related_name="+")

    class Meta:
        db_table = "curriculum_requirement_courses"
        constraints = [
            models.UniqueConstraint(
                fields=["requirement", "course"],
                name="curriculum_requirement_courses_curriculum_requirement_id_course",
            ),
        ]
