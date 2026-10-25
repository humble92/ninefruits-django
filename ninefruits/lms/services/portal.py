"""Platform course links shown in the portal (original ``SectionDetail`` and ``MyTeaching``): only
linked courses with a URL."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable
from typing import Any

from django.http import HttpRequest
from django.utils.html import format_html_join
from django.utils.translation import gettext as _

from ninefruits.lms.enums import LinkStatus
from ninefruits.lms.models import LmsCourseLink


def _linked() -> Any:
    return (
        LmsCourseLink.objects.filter(status=LinkStatus.LINKED, external_url__isnull=False)
        .exclude(external_url="")
        .select_related("platform")
        .order_by("platform__code", "pk")
    )


def course_links_for(section: Any, user: Any = None) -> list[LmsCourseLink]:
    """The section's linked platform courses (the section page link)."""
    links = _linked().filter(section_id=section.pk)
    if user is not None:
        links = links.visible_to(user)
    return list(links)


def linked_courses_by_section(section_ids: Iterable[int], user: Any = None) -> dict[int, list[LmsCourseLink]]:
    links = _linked().filter(section_id__in=list(section_ids))
    if user is not None:
        links = links.visible_to(user)
    grouped: dict[int, list[LmsCourseLink]] = defaultdict(list)
    for link in links:
        grouped[link.section_id].append(link)
    return dict(grouped)


def open_course_label(link: LmsCourseLink) -> str:
    return _("Open the course on %(platform)s") % {"platform": link.platform}


def register_teaching_column() -> None:
    """The LMS link per section on the portal teaching page (original ``my-teaching``)."""
    from ninefruits.offering.teaching import register_column

    def render_links(request: HttpRequest, section: Any) -> str:
        links = course_links_for(section, request.user)
        if not links:
            return "-"
        return format_html_join(
            " ",
            '<a href="{}" target="_blank" rel="noopener" class="text-xs underline" title="{}">LMS</a>',
            ((link.external_url, open_course_label(link)) for link in links),
        )

    register_column("lms", "LMS", render_links, order=90)


def portal_links(section: Any, user: Any) -> list[dict[str, str]]:
    """URL and label of the section's linked courses (the portal section page)."""
    return [
        {"url": str(link.external_url), "label": open_course_label(link)} for link in course_links_for(section, user)
    ]
