"""Which sections are linked to which platform courses, and their last sync (original Filament
``LmsCourseLinkResource``). Links are made by the synchronization, never by hand; the row action
**Synchronize again** pushes the course, its instructors and students again."""

from __future__ import annotations

from typing import Any, ClassVar

from django import forms
from django.contrib import admin, messages
from django.core.exceptions import PermissionDenied
from django.http import HttpRequest, HttpResponse, HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.urls import reverse
from django.utils.html import format_html
from django.utils.translation import gettext, pgettext_lazy
from django.utils.translation import gettext_lazy as _
from unfold.decorators import action, display

from ninefruits.adminpanel.mixins import ReadOnlyCatalogAdmin
from ninefruits.adminpanel.navigation import NavigationGroup
from ninefruits.institution.admin_support import render_action_form
from ninefruits.lms.actions import SyncSection
from ninefruits.lms.enums import LinkStatus
from ninefruits.lms.models import LmsCourseLink, LmsPlatform
from ninefruits.registration.admin.common import AnyTermFilter
from ninefruits.security.enums import Permission


class PlatformFilter(admin.SimpleListFilter):
    title = _("LMS platform")
    parameter_name = "platform"

    def lookups(self, request: HttpRequest, model_admin: Any) -> list[tuple[Any, Any]]:
        return [(str(pk), code) for pk, code in LmsPlatform.objects.order_by("code").values_list("pk", "code")]

    def queryset(self, request: HttpRequest, queryset: Any) -> Any:
        value = self.value()
        return queryset.filter(platform_id=value) if value else queryset


class LinkStatusFilter(admin.SimpleListFilter):
    title = pgettext_lazy("registration", "Status")
    parameter_name = "status"

    def lookups(self, request: HttpRequest, model_admin: Any) -> list[tuple[Any, Any]]:
        return list(LinkStatus.choices)

    def queryset(self, request: HttpRequest, queryset: Any) -> Any:
        value = self.value()
        return queryset.filter(status=value) if value else queryset


class SectionTermFilter(AnyTermFilter):
    field = "section__term_id"


class ConfirmForm(forms.Form):
    """Nothing to enter: the page asks for confirmation (original ``requiresConfirmation``)."""


def shorten(text: str | None, limit: int) -> str:
    if not text:
        return "-"
    return text if len(text) <= limit else text[: limit - 1] + "…"


@admin.register(LmsCourseLink)
class LmsCourseLinkAdmin(ReadOnlyCatalogAdmin):
    permissions: ClassVar[dict[str, str]] = {"view": Permission.LMS_MANAGE}
    navigation_group = NavigationGroup.LMS
    navigation_icon = "link"
    navigation_order = 20
    list_display = (
        "platform_code",
        "term_code",
        "section_label",
        "external_course_id_column",
        "external_url_column",
        "status_column",
        "last_synced_at",
        "last_error_column",
    )
    list_display_links = None
    list_filter = (PlatformFilter, LinkStatusFilter, SectionTermFilter)
    list_select_related = ("platform", "section__course", "section__term")
    search_fields = ("section__course__code",)
    ordering = ("-last_synced_at", "-id")
    actions_row = ("resync_row",)

    def has_view_permission(self, request: HttpRequest, obj: Any = None) -> bool:
        return bool(request.user.has_perm("view_any", LmsCourseLink))

    @display(description=_("LMS platform"), ordering="platform__code")
    def platform_code(self, obj: LmsCourseLink) -> str:
        return obj.platform.code

    @display(description=_("term"), ordering="section__term__code")
    def term_code(self, obj: LmsCourseLink) -> str:
        return obj.section.term.code

    @display(description=pgettext_lazy("offering", "Section"), ordering="section__course__code")
    def section_label(self, obj: LmsCourseLink) -> str:
        return obj.section.label()

    @display(description=_("Course id on the platform"))
    def external_course_id_column(self, obj: LmsCourseLink) -> str:
        return obj.external_course_id or "-"

    @display(description=_("Course URL"))
    def external_url_column(self, obj: LmsCourseLink) -> str:
        if not obj.external_url:
            return "-"
        return format_html(
            '<a href="{}" target="_blank" rel="noopener" class="underline">{}</a>',
            obj.external_url,
            shorten(obj.external_url, 40),
        )

    @display(
        description=pgettext_lazy("registration", "Status"),
        label={LinkStatus.LINKED.value: "success", LinkStatus.FAILED.value: "danger", LinkStatus.PENDING.value: "info"},
    )
    def status_column(self, obj: LmsCourseLink) -> tuple[str, str]:
        return obj.status, str(LinkStatus(obj.status).label)

    @display(description=_("Last error"))
    def last_error_column(self, obj: LmsCourseLink) -> str:
        return shorten(obj.last_error, 40)

    # -- synchronize again ------------------------------------------------------------------------
    def has_resync_row_permission(self, request: HttpRequest, object_id: Any = None) -> bool:
        return bool(request.user.has_perm("resync", LmsCourseLink))

    @action(description=_("Synchronize again"), url_path="resync", permissions=["resync_row"], icon="sync")
    def resync_row(self, request: HttpRequest, object_id: Any) -> HttpResponse:
        link = get_object_or_404(self.get_queryset(request).select_related("platform", "section__course"), pk=object_id)
        if not request.user.has_perm("resync", link):
            raise PermissionDenied
        back = reverse("admin:lms_lmscourselink_changelist")
        form = ConfirmForm(request.POST if request.method == "POST" else None)
        if request.method == "POST" and form.is_valid():
            try:
                summary = SyncSection().handle(link.platform, link.section, actor=request.user)
            except PermissionDenied:
                raise
            except Exception as error:
                messages.error(request, gettext("Synchronization failed: %(error)s") % {"error": error})
            else:
                messages.success(
                    request, gettext("Synchronized: %(members)s member(s).") % {"members": summary["members"]}
                )
            return HttpResponseRedirect(back)
        return render_action_form(
            self,
            request,
            form,
            gettext("Synchronize again"),
            back,
            subtitle=f"{link.platform.code} · {link.section.label()}",
            description=gettext("Pushes the course, its instructors and its enrolled students to the platform again."),
        )
