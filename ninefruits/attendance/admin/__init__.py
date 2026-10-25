"""The section page's class meetings tab (original Filament ``ClassMeetingsRelationManager`` of the
sections resource), mixed into ``SectionAdmin``.

The meetings of the section with how many attendance records each has. Staff with
``sections.manage`` covering the section generate them (the **Generate meetings** button), cancel
one with a reason and restore it; the instructors do the same in the portal."""

from __future__ import annotations

import contextvars
from typing import Any

from django import forms
from django.core.exceptions import PermissionDenied
from django.db.models import Count
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404
from django.template.loader import render_to_string
from django.urls import path, reverse
from django.utils.translation import gettext as _
from django.utils.translation import gettext_lazy, pgettext, pgettext_lazy
from unfold.decorators import action, display
from unfold.widgets import UnfoldAdminTextareaWidget

from ninefruits.attendance.actions import GenerateClassMeetings, ManageClassMeetings
from ninefruits.attendance.models import ClassMeeting

_request: contextvars.ContextVar[HttpRequest | None] = contextvars.ContextVar("section_meetings_request", default=None)

REASON_MAX = 500


class CancelMeetingForm(forms.Form):
    reason = forms.CharField(
        label=pgettext_lazy("common", "Reason"),
        max_length=REASON_MAX,
        widget=UnfoldAdminTextareaWidget(attrs={"rows": 3}),
    )


class ConfirmForm(forms.Form):
    """Nothing to enter: the page asks for confirmation (original ``requiresConfirmation``)."""


def _section_url(section_id: Any) -> str:
    return reverse("admin:offering_section_change", args=[section_id])


def meeting_rows(request: HttpRequest, section: Any) -> list[dict[str, Any]]:
    can_edit = section.is_manageable_by(request.user)
    meetings = (
        ClassMeeting.objects.visible_to(request.user)
        .filter(section_id=section.pk)
        .select_related("room__building")
        .annotate(records_count=Count("records"))
        .order_by("meeting_date", "start_time")
    )
    rows = []
    for meeting in meetings:
        rows.append(
            {
                "meeting": meeting,
                "date": meeting.meeting_date,
                "time": meeting.time_label(),
                "room": meeting.room_label() or "-",
                "status": meeting.get_status_display(),
                "is_cancelled": meeting.is_cancelled,
                "recorded": meeting.records_count,
                "reason": meeting.cancel_reason or "-",
                "cancel_url": (
                    reverse("admin:offering_section_class_meeting_cancel", args=[section.pk, meeting.pk])
                    if can_edit and not meeting.is_cancelled
                    else None
                ),
                "restore_url": (
                    reverse("admin:offering_section_class_meeting_restore", args=[section.pk, meeting.pk])
                    if can_edit and meeting.is_cancelled
                    else None
                ),
            }
        )
    return rows


class SectionClassMeetingsMixin:
    """The class meetings tab and its buttons on the section page."""

    class_meetings_actions_detail = ("generate_class_meetings",)
    class_meetings_readonly_fields = ("class_meetings_table",)

    def class_meetings_fieldsets(self, request: HttpRequest, obj: Any) -> list[Any]:
        _request.set(request)
        if obj is None or obj.pk is None:
            return []
        return [(_("Class meetings"), {"classes": ["tab"], "fields": ["class_meetings_table"]})]

    @display(description="")
    def class_meetings_table(self, obj: Any) -> str:
        request = _request.get()
        if request is None or obj is None or obj.pk is None:
            return ""
        return render_to_string("attendance/admin/class_meetings.html", {"rows": meeting_rows(request, obj)})

    def _meetings_section(self, request: HttpRequest, object_id: Any) -> Any:
        from ninefruits.offering.models import Section

        section = get_object_or_404(Section.objects.select_related("course", "session"), pk=object_id)
        if not section.is_manageable_by(request.user):
            raise PermissionDenied
        return section

    def has_generate_class_meetings_permission(self, request: HttpRequest, object_id: Any = None) -> bool:
        from ninefruits.offering.models import Section
        from ninefruits.security.enums import Permission

        if object_id is None:
            return bool(request.user.has_perm(Permission.SECTIONS_MANAGE))
        section = Section.objects.filter(pk=object_id).first()
        return section is not None and section.is_manageable_by(request.user)

    @action(
        description=gettext_lazy("Generate meetings"),
        url_path="generate-class-meetings",
        permissions=["generate_class_meetings"],
        icon="calendar_month",
    )
    def generate_class_meetings(self, request: HttpRequest, object_id: Any) -> HttpResponse:
        from ninefruits.registration.admin.common import run_form

        section = self._meetings_section(request, object_id)
        form = ConfirmForm(request.POST if request.method == "POST" else None)

        def perform(form: Any) -> str:
            created = GenerateClassMeetings().for_section(section, request.user)
            return _("%(count)s meeting(s) created.") % {"count": created}

        return run_form(
            self,
            request,
            form,
            _("Generate meetings"),
            _section_url(section.pk),
            perform,
            subtitle=section.label(),
            description=_(
                "Creates one meeting per occurrence of the weekly meeting times within their dates. "
                "Existing meetings and their attendance are kept."
            ),
        )

    def _class_meeting(self, request: HttpRequest, section_id: int, meeting_id: int) -> tuple[Any, ClassMeeting]:
        section = self._meetings_section(request, section_id)
        meeting = get_object_or_404(ClassMeeting.objects.select_related("section"), pk=meeting_id, section=section)
        return section, meeting

    def cancel_class_meeting(self, request: HttpRequest, section_id: int, meeting_id: int) -> HttpResponse:
        from ninefruits.registration.admin.common import run_form

        section, meeting = self._class_meeting(request, section_id, meeting_id)
        form = CancelMeetingForm(request.POST or None)

        def perform(form: Any) -> str:
            ManageClassMeetings().cancel(meeting, request.user, form.cleaned_data["reason"])
            return _("Meeting cancelled.")

        return run_form(
            self,
            request,
            form,
            pgettext("attendance", "Cancel"),
            _section_url(section.pk),
            perform,
            subtitle=f"{section.label()} · {meeting.meeting_date.isoformat()} {meeting.time_label()}",
        )

    def restore_class_meeting(self, request: HttpRequest, section_id: int, meeting_id: int) -> HttpResponse:
        from ninefruits.registration.admin.common import run_form

        section, meeting = self._class_meeting(request, section_id, meeting_id)
        form = ConfirmForm(request.POST if request.method == "POST" else None)

        def perform(form: Any) -> str:
            ManageClassMeetings().restore(meeting, request.user)
            return _("Meeting restored.")

        return run_form(
            self,
            request,
            form,
            _("Restore"),
            _section_url(section.pk),
            perform,
            subtitle=f"{section.label()} · {meeting.meeting_date.isoformat()} {meeting.time_label()}",
        )

    def get_urls(self) -> list[Any]:
        info = self.model._meta.app_label, self.model._meta.model_name  # type: ignore[attr-defined]
        site = self.admin_site  # type: ignore[attr-defined]
        return [
            path(
                "<int:section_id>/class-meetings/<int:meeting_id>/cancel/",
                site.admin_view(self.cancel_class_meeting),
                name="{}_{}_class_meeting_cancel".format(*info),
            ),
            path(
                "<int:section_id>/class-meetings/<int:meeting_id>/restore/",
                site.admin_view(self.restore_class_meeting),
                name="{}_{}_class_meeting_restore".format(*info),
            ),
            *super().get_urls(),  # type: ignore[misc]
        ]
