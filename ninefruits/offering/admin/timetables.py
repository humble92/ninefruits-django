"""Weekly timetable of a room or an instructor in a term, for planning and checking (original
Filament page ``ViewTimetables``, ``/admin/offering/timetables``)."""

from __future__ import annotations

from typing import Any

from django import forms
from django.contrib import admin
from django.core.exceptions import PermissionDenied
from django.http import HttpRequest, HttpResponse
from django.shortcuts import render
from django.utils.translation import gettext as gettext_now
from django.utils.translation import gettext_lazy as _
from unfold.widgets import UnfoldAdminSelectWidget

from ninefruits.facility.models import Room
from ninefruits.offering.enums import SectionStatus
from ninefruits.offering.models import SectionMeeting
from ninefruits.offering.services import Timetable, room_label
from ninefruits.security.enums import Permission

from .sections import default_term_id, instructor_choices, term_choices


def can_view_timetables(request: HttpRequest) -> bool:
    user = request.user
    return bool(user.has_perm(Permission.SECTIONS_VIEW) or user.has_perm(Permission.SECTIONS_MANAGE))


class TimetableForm(forms.Form):
    term = forms.TypedChoiceField(
        label=_("term"), coerce=int, required=False, empty_value=None, widget=UnfoldAdminSelectWidget
    )
    mode = forms.ChoiceField(label=_("Show"), required=False, widget=UnfoldAdminSelectWidget)
    target = forms.TypedChoiceField(
        label=_("Room"), coerce=int, required=False, empty_value=None, widget=UnfoldAdminSelectWidget
    )

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.fields["term"].choices = [("", "---------"), *term_choices()]  # type: ignore[attr-defined]
        self.fields["mode"].choices = [("room", _("Room")), ("instructor", _("instructor"))]  # type: ignore[attr-defined]
        mode = self.data.get("mode") or "room"
        if mode == "instructor":
            self.fields["target"].label = gettext_now("instructor").capitalize()
            choices = [(pk, label) for pk, label in instructor_choices()]
        else:
            rooms = Room.objects.filter(is_active=True).select_related("building")
            choices = sorted(((room.pk, f"{room.building.code}-{room.code}") for room in rooms), key=lambda r: r[1])
        self.fields["target"].choices = [("", "---------"), *choices]  # type: ignore[attr-defined]


def build_timetable(term_id: int | None, mode: str, target_id: int | None) -> dict[str, Any] | None:
    if term_id is None or target_id is None:
        return None
    meetings = (
        SectionMeeting.objects.filter(is_active=True, section__term_id=term_id)
        .exclude(section__status=SectionStatus.CANCELLED)
        .select_related("section__course", "section__version", "section__session", "room__building")
    )
    if mode == "instructor":
        meetings = meetings.filter(section__instructor_assignments__instructor_id=target_id).distinct()
    else:
        meetings = meetings.filter(room_id=target_id)

    def describe(meeting: SectionMeeting) -> tuple[str, str]:
        section = meeting.section
        parts = [str(section.version.title or ""), room_label(meeting)]
        if not section.session.is_full_term:
            parts.append(section.session.code)
        return section.label(), " · ".join(part for part in parts if part)

    return Timetable().build(list(meetings), describe)


def timetables_view(request: HttpRequest) -> HttpResponse:
    if not can_view_timetables(request):
        raise PermissionDenied
    data = request.GET.copy()
    if "term" not in data:
        data["term"] = str(default_term_id() or "")
    data.setdefault("mode", "room")
    form = TimetableForm(data)
    timetable = None
    if form.is_valid():
        timetable = build_timetable(
            form.cleaned_data.get("term"), form.cleaned_data.get("mode") or "room", form.cleaned_data.get("target")
        )
    context = {
        **admin.site.each_context(request),
        "title": _("Timetables"),
        "form": form,
        "timetable": timetable,
    }
    return render(request, "offering/admin/timetables.html", context)
