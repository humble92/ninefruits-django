"""Grade progress per section (original Filament ``SectionGradeResource`` on the section model): a
proxy of ``offering.Section`` so the grades screen has its own admin next to the section
screens."""

from __future__ import annotations

from typing import Any, Self

from django.utils.translation import gettext_lazy as _

from ninefruits.offering.models import Section
from ninefruits.offering.models.section import SectionQuerySet
from ninefruits.security.enums import Permission


class SectionGradeQuerySet(SectionQuerySet):
    def visible_to(self, user: Any) -> Self:
        """Sections with registered or completed students, offered by units in the user's
        ``grades.view`` or ``grades.manage`` scope."""
        from ninefruits.registration.enums import EnrollmentStatus
        from ninefruits.registration.models import Enrollment

        with_students = Enrollment.objects.filter(
            status__in=[EnrollmentStatus.ENROLLED, EnrollmentStatus.COMPLETED]
        ).values("section_id")
        return self.in_scope_of(user, Permission.GRADES_VIEW, Permission.GRADES_MANAGE).filter(pk__in=with_students)


class SectionGrade(Section):
    objects = SectionGradeQuerySet.as_manager()  # type: ignore[misc]  # a proxy may narrow the manager

    class Meta:
        proxy = True
        verbose_name = _("grade progress")
        verbose_name_plural = _("grade progress")
