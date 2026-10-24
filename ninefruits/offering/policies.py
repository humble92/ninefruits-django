"""Section policy (original ``App\\Policies\\Offering\\SectionPolicy``): sections are managed by
staff of the offering unit (``sections.manage`` in scope); their instructors write the syllabus."""

from __future__ import annotations

from typing import Any

from ninefruits.offering.enums import SectionStatus
from ninefruits.security.enums import Permission
from ninefruits.security.policies import Policy, register


class SectionPolicy(Policy):
    def view_any(self, user: Any, obj: Any) -> bool:
        return bool(user.has_perm(Permission.SECTIONS_VIEW) or user.has_perm(Permission.SECTIONS_MANAGE))

    def view(self, user: Any, obj: Any) -> bool:
        from ninefruits.offering.models import Section

        if obj is None:
            return self.view_any(user, obj)
        return Section.objects.filter(pk=obj.pk).manageable_by(user).exists()

    def create(self, user: Any, obj: Any) -> bool:
        return bool(user.has_perm(Permission.SECTIONS_MANAGE))

    def update(self, user: Any, obj: Any) -> bool:
        return obj is not None and obj.is_manageable_by(user)

    def edit_syllabus(self, user: Any, obj: Any) -> bool:
        return obj is not None and (obj.is_taught_by(user) or obj.is_manageable_by(user))

    def delete(self, user: Any, obj: Any) -> bool:
        """Only drafts; published sections are cancelled instead."""
        return obj is not None and obj.status == SectionStatus.DRAFT and obj.is_manageable_by(user)


class SectionPartPolicy(Policy):
    """Meetings, instructors, seat groups and syllabi follow their section."""

    def view(self, user: Any, obj: Any) -> bool:
        return obj is None or SectionPolicy().view(user, obj.section)

    def update(self, user: Any, obj: Any) -> bool:
        return obj is not None and obj.section.is_manageable_by(user)

    def delete(self, user: Any, obj: Any) -> bool:
        return self.update(user, obj)


def register_policies() -> None:
    register("offering.section", SectionPolicy())
    for label in ("offering.sectionmeeting", "offering.sectioninstructor", "offering.sectionseatgroup"):
        register(label, SectionPartPolicy())
