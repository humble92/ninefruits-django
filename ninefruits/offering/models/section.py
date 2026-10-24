"""Sections and what belongs to them (original ``App\\Models\\Offering\\*``, ADR 0009).

A section is a course offered in a term session (legacy SFOPOBJECT). Its deadlines are the
session's windows; course data (title, credits) comes from the version valid at the session start.
The database keeps the session in the section's term and the version of the section's course
(composite foreign keys), refuses a room booked twice (exclusion constraint
``section_meetings_room_excl``) and an instructor at two places (triggers on ``section_meetings``
and ``section_instructors``), and frees the meetings of a cancelled section (trigger on
``sections``)."""

from __future__ import annotations

from datetime import datetime, time
from typing import Any, Self

from django.conf import settings
from django.db import models
from django.db.models import Q
from django.utils.translation import gettext_lazy as _
from django.utils.translation import pgettext_lazy

from ninefruits.core.models import TimeStampedModel, VisibleQuerySet
from ninefruits.core.targeting import TargetCriteriaField, TargetSubject
from ninefruits.grading.enums import EvaluationMethod
from ninefruits.i18n.fields import TranslatableJSONField
from ninefruits.offering.enums import InstructorRole, SectionStatus
from ninefruits.security.enums import Permission


def scope_org_unit_ids(scope: Any) -> list[int]:
    """Org units of a permission scope; a program scope means the program's unit (sections belong
    to units, not programs)."""
    from ninefruits.organization.models import Program

    program_units = (
        list(Program.objects.filter(pk__in=scope.program_ids).values_list("org_unit_id", flat=True))
        if scope.program_ids
        else []
    )
    return list(dict.fromkeys([*scope.org_unit_ids, *program_units]))


def _scope(user: Any, *permissions: Permission) -> Any:
    from ninefruits.security.services.authorization import PermissionScope, authorization

    scope = PermissionScope.none()
    if user is None or not getattr(user, "is_authenticated", False):
        return scope
    for permission in permissions:
        scope = scope.merge(authorization().scope_for(user, permission))
    return scope


class SectionQuerySet(VisibleQuerySet):
    def published(self) -> Self:
        return self.filter(status=SectionStatus.PUBLISHED)

    def taught_by(self, person_id: int | None) -> Self:
        if person_id is None:
            return self.none()
        return self.filter(instructor_assignments__instructor__person_id=person_id).distinct()

    def in_scope_of(self, user: Any, *permissions: Permission) -> Self:
        """Sections whose offering unit is in the user's scope for any of the permissions
        (original ``Section::constrainToScope``)."""
        scope = _scope(user, *permissions)
        if scope.is_global:
            return self
        return self.filter(org_unit_id__in=scope_org_unit_ids(scope))

    def manageable_by(self, user: Any) -> Self:
        """Staff see sections of units in their ``sections.view`` or ``sections.manage`` scope
        (original ``Section::constrainManageableBy``)."""
        return self.in_scope_of(user, Permission.SECTIONS_VIEW, Permission.SECTIONS_MANAGE)

    def visible_to(self, user: Any) -> Self:
        """Staff scope, plus published sections and the user's own teaching (the portal catalog
        and section pages)."""
        scope = _scope(user, Permission.SECTIONS_VIEW, Permission.SECTIONS_MANAGE)
        if scope.is_global:
            return self
        condition = Q(status=SectionStatus.PUBLISHED) | Q(org_unit_id__in=scope_org_unit_ids(scope))
        person_id = getattr(user, "person_id", None)
        if person_id is not None:
            condition |= Q(pk__in=Section.objects.taught_by(person_id).values("pk"))
        return self.filter(condition)


class Section(TimeStampedModel):
    term = models.ForeignKey("term.Term", on_delete=models.RESTRICT, related_name="sections", verbose_name=_("term"))
    session = models.ForeignKey(
        "term.TermSession",
        on_delete=models.RESTRICT,
        related_name="sections",
        db_column="term_session_id",
        # The real constraint is the composite (term_session_id, term_id) foreign key.
        db_constraint=False,
        verbose_name=pgettext_lazy("offering", "Session"),
        help_text=_("Moving to another session takes its dates and the course version in effect when it starts."),
    )
    course = models.ForeignKey(
        "curriculum.Course", on_delete=models.RESTRICT, related_name="sections", verbose_name=_("course")
    )
    version = models.ForeignKey(
        "curriculum.CourseVersion",
        on_delete=models.RESTRICT,
        related_name="sections",
        db_column="course_version_id",
        # The real constraint is the composite (course_version_id, course_id) foreign key.
        db_constraint=False,
    )
    section_code = models.CharField(_("Section number"), max_length=16)
    org_unit = models.ForeignKey(
        "organization.OrgUnit",
        on_delete=models.RESTRICT,
        related_name="sections",
        verbose_name=_("Offering unit"),
        help_text=_("Unit whose staff manage the section; the course's unit by default."),
    )
    capacity = models.IntegerField(pgettext_lazy("offering", "Capacity"))
    status = models.CharField(
        pgettext_lazy("offering", "Status"), max_length=16, choices=SectionStatus.choices, default=SectionStatus.DRAFT
    )
    eligibility = TargetCriteriaField(
        _("Who may register"), null=True, blank=True, help_text=_("Empty: everyone. Registration (Phase 5) checks it.")
    )
    exclusion = TargetCriteriaField(
        _("Who may not register"),
        null=True,
        blank=True,
        help_text=_("Students matching this cannot register, e.g. the course's own majors for a general course."),
    )
    instruction_language = models.CharField(
        _("Language of instruction"), max_length=16, null=True, blank=True, help_text=_("e.g. ko, en")
    )
    note = TranslatableJSONField(pgettext_lazy("offering", "Note"), null=True, blank=True, max_length=2000)
    copied_from_section = models.ForeignKey(
        "self", on_delete=models.SET_NULL, null=True, blank=True, related_name="copies", editable=False
    )
    enrolled_count = models.IntegerField(default=0, editable=False)
    waitlist_capacity = models.IntegerField(
        _("Waitlist size"),
        default=0,
        help_text=_(
            "0 means no waitlist. Freed seats go to waiting students in order, after all rules are checked again."
        ),
    )
    evaluation_method = models.CharField(
        _("Evaluation"), max_length=16, choices=EvaluationMethod.choices, default=EvaluationMethod.ABSOLUTE
    )
    grade_exception_reason = models.TextField(null=True, blank=True, editable=False)
    grade_exception_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="+", editable=False
    )
    grade_exception_at = models.DateTimeField(null=True, blank=True, editable=False)
    instructors = models.ManyToManyField(
        "person.Instructor", through="SectionInstructor", related_name="sections", blank=True
    )

    objects = SectionQuerySet.as_manager()

    class Meta:
        db_table = "sections"
        ordering = ["term_id", "course__code", "section_code"]
        verbose_name = _("section")
        verbose_name_plural = _("sections")
        constraints = [
            models.UniqueConstraint(
                fields=["term", "course", "section_code"], name="sections_term_id_course_id_section_code_unique"
            ),
        ]

    def __str__(self) -> str:
        return self.label()

    @property
    def term_session_id(self) -> int | None:
        return self.session_id

    @term_session_id.setter
    def term_session_id(self, value: int | None) -> None:
        self.session_id = value

    @property
    def course_version_id(self) -> int | None:
        return self.version_id

    @course_version_id.setter
    def course_version_id(self, value: int | None) -> None:
        self.version_id = value

    @property
    def section_status(self) -> SectionStatus:
        return SectionStatus(self.status)

    def label(self) -> str:
        """Course code and section number, e.g. "CSE2010-01"."""
        return f"{self.course.code}-{self.section_code}"

    def admits(self, subject: TargetSubject) -> bool:
        """Whether a student may take the section by its include and exclude conditions (seat
        groups and the other registration rules are checked at registration)."""
        return self.eligibility.matches(subject) and (
            self.exclusion.is_everyone() or not self.exclusion.matches(subject)
        )

    def is_in_scope_of(self, user: Any, permission: Permission) -> bool:
        """Whether the user holds the permission in a scope covering the offering unit."""
        scope = _scope(user, permission)
        return bool(scope.is_global or self.org_unit_id in scope_org_unit_ids(scope))

    def is_manageable_by(self, user: Any) -> bool:
        return self.is_in_scope_of(user, Permission.SECTIONS_MANAGE)

    def is_registration_manageable_by(self, user: Any) -> bool:
        return self.is_in_scope_of(user, Permission.REGISTRATION_MANAGE)

    def is_taught_by(self, user: Any) -> bool:
        person_id = getattr(user, "person_id", None)
        return (
            person_id is not None
            and self.pk is not None
            and SectionInstructor.objects.filter(section_id=self.pk, instructor__person_id=person_id).exists()
        )


class SectionInstructor(TimeStampedModel):
    section = models.ForeignKey(Section, on_delete=models.CASCADE, related_name="instructor_assignments")
    instructor = models.ForeignKey(
        "person.Instructor",
        on_delete=models.RESTRICT,
        related_name="section_assignments",
        verbose_name=_("instructor"),
    )
    role = models.CharField(
        pgettext_lazy("offering", "Role"), max_length=16, choices=InstructorRole.choices, default=InstructorRole.PRIMARY
    )

    objects = VisibleQuerySet.as_manager()

    class Meta:
        db_table = "section_instructors"
        ordering = ["id"]
        verbose_name = pgettext_lazy("offering", "Instructors")
        verbose_name_plural = pgettext_lazy("offering", "Instructors")
        constraints = [
            models.UniqueConstraint(
                fields=["section", "instructor"], name="section_instructors_section_id_instructor_id_unique"
            ),
        ]

    def __str__(self) -> str:
        return f"{self.section_id}:{self.instructor_id}"


def minutes(value: time | str) -> int:
    if isinstance(value, str):
        hours, mins = (int(part) for part in value.split(":")[:2])
        return hours * 60 + mins
    return value.hour * 60 + value.minute


class SectionMeeting(TimeStampedModel):
    """A weekly meeting: weekday, wall-clock times, room and dates (normally the session's)."""

    section = models.ForeignKey(Section, on_delete=models.CASCADE, related_name="meetings")
    #: ISO-8601, 1 = Monday.
    weekday = models.SmallIntegerField(_("Day"))
    start_time = models.TimeField(pgettext_lazy("offering", "Start"))
    end_time = models.TimeField(_("End"))
    room = models.ForeignKey(
        "facility.Room",
        on_delete=models.RESTRICT,
        null=True,
        blank=True,
        related_name="section_meetings",
        verbose_name=_("Room"),
    )
    start_date = models.DateField(_("Start date"))
    end_date = models.DateField(_("End date"))
    is_active = models.BooleanField(default=True, editable=False)

    objects = VisibleQuerySet.as_manager()

    class Meta:
        db_table = "section_meetings"
        ordering = ["weekday", "start_time"]
        verbose_name = _("meeting")
        verbose_name_plural = _("meeting times")

    def __str__(self) -> str:
        return self.time_label()

    def time_label(self) -> str:
        """Start and end, e.g. "09:00–10:15"."""
        return f"{_hhmm(self.start_time)}–{_hhmm(self.end_time)}"

    def start_minute(self) -> int:
        return minutes(self.start_time)

    def end_minute(self) -> int:
        return minutes(self.end_time)


def _hhmm(value: time | str) -> str:
    return value[:5] if isinstance(value, str) else value.strftime("%H:%M")


class SectionSeatGroup(TimeStampedModel):
    """Seats reserved for a group of students (e.g. 30 for majors), until ``releases_at`` when
    unused seats open to everyone. Enforced by registration (Phase 5)."""

    section = models.ForeignKey(Section, on_delete=models.CASCADE, related_name="seat_groups")
    name = TranslatableJSONField(pgettext_lazy("reference", "Name"))
    capacity = models.IntegerField(pgettext_lazy("offering", "Capacity"))
    eligibility = TargetCriteriaField(_("Students the seats are for"), null=True, blank=True)
    releases_at = models.DateTimeField(
        _("Opens to everyone at"),
        null=True,
        blank=True,
        help_text=_("Unused reserved seats become open seats at this time."),
    )
    sort_order = models.IntegerField(_("Order"), default=0)
    enrolled_count = models.IntegerField(default=0, editable=False)
    release_processed_at = models.DateTimeField(null=True, blank=True, editable=False)

    objects = VisibleQuerySet.as_manager()

    class Meta:
        db_table = "section_seat_groups"
        ordering = ["sort_order", "id"]
        verbose_name = _("seat group")
        verbose_name_plural = _("reserved seats")

    def __str__(self) -> str:
        return str(self.name or "")

    def is_reserved_at(self, at: datetime) -> bool:
        """Still reserved for its group at the time (``releases_at`` empty: always reserved)."""
        return self.releases_at is None or self.releases_at > at

    def save(self, *args: Any, **kwargs: Any) -> None:
        # timestamp(0) column: whole seconds.
        if isinstance(self.releases_at, datetime) and self.releases_at.microsecond:
            self.releases_at = self.releases_at.replace(microsecond=0)
        super().save(*args, **kwargs)


class Syllabus(TimeStampedModel):
    """The syllabus of a section, written by its instructors in one language. Content keys:
    overview, objectives, assessment (list of ``{item, weight}``), materials, weekly_plan (list
    of ``{week, topic}``), policies. Students see it once published."""

    PARTS = ("overview", "objectives", "materials", "policies")

    section = models.OneToOneField(Section, on_delete=models.CASCADE, related_name="syllabus")
    language = models.CharField(pgettext_lazy("offering", "Language"), max_length=16)
    content = models.JSONField(default=dict)
    published_at = models.DateTimeField(null=True, blank=True)
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )

    objects = VisibleQuerySet.as_manager()

    class Meta:
        db_table = "syllabi"
        verbose_name = _("Syllabus")
        verbose_name_plural = _("Syllabus")

    def __str__(self) -> str:
        return f"{self.section_id} ({self.language})"

    @property
    def is_published(self) -> bool:
        return self.published_at is not None
