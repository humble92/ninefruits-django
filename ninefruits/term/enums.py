"""Term enums (original ``App\\Domain\\Term\\Enums``)."""

from __future__ import annotations

from django.db import models
from django.utils.translation import gettext_lazy as _
from django.utils.translation import pgettext_lazy


class TermStatus(models.TextChoices):
    """Operating state of a term. Changed only by administrator actions (``ChangeTermStatus``),
    independent of dates and term windows."""

    PLANNED = "planned", _("Planned")
    PUBLISHED = "published", pgettext_lazy("reference.term_statuses", "Published")
    GRADES_CLOSED = "grades_closed", _("Grades closed")
    ARCHIVED = "archived", _("Archived")

    def allowed_next(self) -> list[TermStatus]:
        return list(_TRANSITIONS[self])

    def can_move_to(self, status: TermStatus) -> bool:
        return TermStatus(status) in _TRANSITIONS[self]


_TRANSITIONS: dict[TermStatus, tuple[TermStatus, ...]] = {
    TermStatus.PLANNED: (TermStatus.PUBLISHED,),
    TermStatus.PUBLISHED: (TermStatus.PLANNED, TermStatus.GRADES_CLOSED),
    TermStatus.GRADES_CLOSED: (TermStatus.PUBLISHED, TermStatus.ARCHIVED),
    TermStatus.ARCHIVED: (),
}

#: Terms whose windows can open.
OPEN_STATUSES: tuple[TermStatus, ...] = (TermStatus.PUBLISHED, TermStatus.GRADES_CLOSED)


class TermWindowType(models.TextChoices):
    """Business periods within a term (legacy SSOBJDATE columns). Windows about courses belong to
    a term session, because a course's deadlines follow its session (a second-half course has
    its own add/drop and grading); the others concern students or the whole term."""

    REGISTRATION_CART = "registration_cart", _("Registration cart")
    REGISTRATION = "registration", _("Registration")
    ADD_DROP = "add_drop", _("Add/drop")
    WITHDRAWAL = "withdrawal", _("Withdrawal")
    GRADE_ENTRY = "grade_entry", _("Grade entry")
    GRADE_APPEAL = "grade_appeal", _("Grade appeal")
    COURSE_EVALUATION = "course_evaluation", pgettext_lazy("reference.term_window_types", "Course evaluation")
    GRADUATION_APPLICATION = "graduation_application", _("Graduation application")
    ADDITIONAL_PROGRAM_APPLICATION = "additional_program_application", _("Second major and minor applications")

    @classmethod
    def course_scoped(cls) -> list[TermWindowType]:
        """Windows that belong to a session (deadlines of the courses in it)."""
        return [cls.ADD_DROP, cls.WITHDRAWAL, cls.GRADE_ENTRY, cls.GRADE_APPEAL, cls.COURSE_EVALUATION]

    def is_course_scoped(self) -> bool:
        return self in TermWindowType.course_scoped()
