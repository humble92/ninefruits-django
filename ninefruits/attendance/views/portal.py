"""Attendance in the portal (original Livewire ``SectionAttendance`` and ``MyAttendance``).

Roster and attendance (``/portal/sections/<id>/attendance/``), for the section's instructors and
the staff who see the section: the roster with photos and attendance totals, the class meetings
(generate from the meeting times, add a make-up class, cancel with a reason, restore), and, with
``?meeting=<id>``, attendance entry for one meeting. The page's forms POST an ``action``; a
successful action keeps its message for the next page and redirects back (the page works without
JavaScript), an action that fails shows the page again with what was entered. With HTMX the block
``#attendance`` is swapped.

My attendance (``/portal/attendance/``): a student's attendance per course for a term, with the
record of each meeting held."""

from __future__ import annotations

from collections.abc import Callable
from datetime import date
from typing import Any

from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied, ValidationError
from django.db.models import Count
from django.http import Http404, HttpRequest, HttpResponse, HttpResponseRedirect
from django.shortcuts import get_object_or_404, render
from django.urls import reverse
from django.utils import timezone
from django.utils.html import format_html
from django.utils.translation import gettext as _
from django.utils.translation import gettext_lazy, pgettext
from django.views import View

from ninefruits.attendance.actions import GenerateClassMeetings, ManageClassMeetings, RecordAttendance
from ninefruits.attendance.enums import AttendanceStatus, ClassMeetingStatus
from ninefruits.attendance.models import AttendanceRecord, ClassMeeting
from ninefruits.attendance.services import AttendanceSummary, SectionRoster
from ninefruits.offering.models import Section

FLASH_KEY = "attendance.flash"
REASON_MAX = 500


def _int(value: Any) -> int | None:
    try:
        return int(value) if value not in (None, "") else None
    except TypeError, ValueError:
        return None


def register_teaching_column() -> None:
    """The roster and attendance link on the portal teaching page (original ``my-teaching``)."""
    from ninefruits.offering.teaching import register_column

    def render_link(request: HttpRequest, section: Any) -> str:
        return format_html(
            '<a href="{}" class="underline">{}</a>',
            reverse("portal:attendance_section", args=[section.pk]),
            pgettext("attendance", "Open"),
        )

    register_column("attendance", gettext_lazy("Roster and attendance"), render_link, order=10)


def photo_person_ids(person_ids: list[int]) -> set[int]:
    """The people among these who have a photo (one query)."""
    from ninefruits.core.morph import morph_type
    from ninefruits.media.models import Media
    from ninefruits.person.models import Person

    return set(
        Media.objects.filter(
            model_type=morph_type(Person), model_id__in=person_ids, collection_name=Person.PHOTO_COLLECTION
        ).values_list("model_id", flat=True)
    )


class SectionAttendanceView(LoginRequiredMixin, View):
    template_name = "attendance/portal/section_attendance.html"

    # -- access ----------------------------------------------------------------------------------
    def _section(self, request: HttpRequest, pk: int) -> Section:
        section: Section = get_object_or_404(
            Section.objects.select_related("course", "version", "term", "session"), pk=pk
        )
        if not SectionRoster.can_view(section, request.user):
            raise PermissionDenied
        return section

    def _meeting(self, section: Section, meeting_id: int | None) -> ClassMeeting | None:
        if meeting_id is None:
            return None
        return ClassMeeting.objects.filter(section_id=section.pk, pk=meeting_id).first()

    def _url(self, section: Section, meeting: ClassMeeting | None = None) -> str:
        url = reverse("portal:attendance_section", args=[section.pk])
        return f"{url}?meeting={meeting.pk}" if meeting is not None else url

    # -- GET -------------------------------------------------------------------------------------
    def get(self, request: HttpRequest, pk: int) -> HttpResponse:
        section = self._section(request, pk)
        meeting = self._meeting(section, _int(request.GET.get("meeting")))
        flash = request.session.pop(FLASH_KEY, None) or {"tone": "success", "message": None}
        return render(request, self.template_name, self._context(request, section, meeting, flash))

    def _context(
        self,
        request: HttpRequest,
        section: Section,
        meeting: ClassMeeting | None,
        flash: dict[str, Any],
        posted: dict[str, dict[int, str]] | None = None,
        new_meeting: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        roster = SectionRoster().enrollments(section)
        summary = AttendanceSummary().for_section(section, roster)
        can_edit = ManageClassMeetings.can_manage(section, request.user)
        photos = photo_person_ids([enrollment.student_record.person_id for enrollment in roster])
        context: dict[str, Any] = {
            "title": f"{_('Roster and attendance')} · {section.label()}",
            "section": section,
            "enrollments": roster,
            "summary": summary,
            "can_edit": can_edit,
            "flash": flash,
            "meeting": meeting,
            "status_options": list(AttendanceStatus),
            "today": timezone.localdate(),
            "reason_max": REASON_MAX,
        }
        if meeting is not None:
            records = {
                record.enrollment_id: record for record in AttendanceRecord.objects.filter(class_meeting=meeting)
            }
            statuses = (posted or {}).get("statuses")
            notes = (posted or {}).get("notes")
            context["entry_rows"] = [
                {
                    "enrollment": enrollment,
                    "record": enrollment.student_record,
                    "status": (
                        statuses.get(enrollment.pk, "")
                        if statuses is not None
                        else (records[enrollment.pk].status if enrollment.pk in records else "")
                    ),
                    "note": (
                        notes.get(enrollment.pk, "")
                        if notes is not None
                        else ((records[enrollment.pk].note or "") if enrollment.pk in records else "")
                    ),
                }
                for enrollment in roster
            ]
            return context
        meetings = list(
            ClassMeeting.objects.filter(section_id=section.pk)
            .select_related("room__building")
            .annotate(records_count=Count("records"))
            .order_by("meeting_date", "start_time")
        )
        context["roster_rows"] = [
            {
                "enrollment": enrollment,
                "record": enrollment.student_record,
                "has_photo": enrollment.student_record.person_id in photos,
                "counts": summary["students"][enrollment.pk],
            }
            for enrollment in roster
        ]
        context["meetings"] = meetings
        context["new_meeting"] = new_meeting or {
            "date": timezone.localdate().isoformat(),
            "start": "09:00",
            "end": "10:50",
        }
        return context

    # -- POST ------------------------------------------------------------------------------------
    ACTIONS = ("save", "mark_all", "generate", "add_meeting", "cancel_meeting", "restore_meeting")

    def post(self, request: HttpRequest, pk: int) -> HttpResponse:
        section = self._section(request, pk)
        action, _sep, argument = request.POST.get("action", "").partition(":")
        if action not in self.ACTIONS:
            raise Http404
        meeting = self._meeting(section, _int(request.POST.get("meeting")))
        if action == "mark_all":
            return self._mark_all(request, section, meeting, argument)
        handler: Callable[[HttpRequest, Section, ClassMeeting | None, str], tuple[str, ClassMeeting | None]] = getattr(
            self, f"_{action}"
        )
        try:
            message, back_to = handler(request, section, meeting, argument)
        except (ValidationError, PermissionDenied) as error:
            text = (
                " ".join(str(message) for message in error.messages)
                if isinstance(error, ValidationError)
                else _("Only the section's instructors and the staff who manage it can do this.")
            )
            context = self._context(
                request,
                section,
                meeting if action == "save" else None,
                {"tone": "error", "message": text},
                posted=self._posted(request, section) if action == "save" else None,
                new_meeting=self._new_meeting(request) if action == "add_meeting" else None,
            )
            return render(request, self.template_name, context)
        request.session[FLASH_KEY] = {"tone": "success", "message": message}
        return HttpResponseRedirect(self._url(section, back_to))

    def _posted(self, request: HttpRequest, section: Section) -> dict[str, dict[int, str]]:
        """The entry form by enrollment id: ``status-<id>`` (radio) and ``note-<id>``. Every
        student of the roster has a status (empty when no radio is chosen), as in the original
        component."""
        statuses: dict[int, str] = {}
        notes: dict[int, str] = {}
        for enrollment in SectionRoster().enrollments(section):
            statuses[enrollment.pk] = (request.POST.get(f"status-{enrollment.pk}") or "").strip()
            notes[enrollment.pk] = (request.POST.get(f"note-{enrollment.pk}") or "").strip()
        return {"statuses": statuses, "notes": notes}

    def _new_meeting(self, request: HttpRequest) -> dict[str, str]:
        return {
            "date": request.POST.get("meeting_date", ""),
            "start": request.POST.get("start_time", ""),
            "end": request.POST.get("end_time", ""),
        }

    def _mark_all(
        self, request: HttpRequest, section: Section, meeting: ClassMeeting | None, status: str
    ) -> HttpResponse:
        """Sets every student of the entry form to one status without saving (original
        ``markAll``); the notes entered stay."""
        if meeting is None:
            raise Http404
        posted = self._posted(request, section)
        value = status if status in AttendanceStatus.values else AttendanceStatus.PRESENT.value
        posted["statuses"] = dict.fromkeys(posted["statuses"], value)
        context = self._context(request, section, meeting, {"tone": "success", "message": None}, posted=posted)
        return render(request, self.template_name, context)

    def _save(
        self, request: HttpRequest, section: Section, meeting: ClassMeeting | None, argument: str
    ) -> tuple[str, ClassMeeting | None]:
        if meeting is None:
            raise Http404
        posted = self._posted(request, section)
        statuses: dict[int, str | None] = {key: value or None for key, value in posted["statuses"].items()}
        notes: dict[int, str | None] = dict(posted["notes"])
        RecordAttendance().save(meeting, statuses, request.user, notes)
        return _("Attendance saved."), meeting

    def _generate(
        self, request: HttpRequest, section: Section, meeting: ClassMeeting | None, argument: str
    ) -> tuple[str, ClassMeeting | None]:
        ManageClassMeetings.authorize(section, request.user)
        created = GenerateClassMeetings().for_section(section, request.user)
        return _("%(count)s meeting(s) created.") % {"count": created}, None

    def _add_meeting(
        self, request: HttpRequest, section: Section, meeting: ClassMeeting | None, argument: str
    ) -> tuple[str, ClassMeeting | None]:
        values = self._new_meeting(request)
        try:
            day = date.fromisoformat(values["date"])
        except ValueError as error:
            raise ValidationError({"meeting_date": _("The date is outside the session.")}) from error
        ManageClassMeetings().add(section, day, values["start"], values["end"], request.user)
        return _("Meeting added."), None

    def _target(self, section: Section, argument: str) -> ClassMeeting:
        return get_object_or_404(ClassMeeting, section_id=section.pk, pk=_int(argument))

    def _cancel_meeting(
        self, request: HttpRequest, section: Section, meeting: ClassMeeting | None, argument: str
    ) -> tuple[str, ClassMeeting | None]:
        target = self._target(section, argument)
        reason = (request.POST.get(f"reason-{target.pk}") or request.POST.get("reason") or "").strip()[:REASON_MAX]
        ManageClassMeetings().cancel(target, request.user, reason)
        return _("Meeting cancelled."), None

    def _restore_meeting(
        self, request: HttpRequest, section: Section, meeting: ClassMeeting | None, argument: str
    ) -> tuple[str, ClassMeeting | None]:
        ManageClassMeetings().restore(self._target(section, argument), request.user)
        return _("Meeting restored."), None


class MyAttendanceView(LoginRequiredMixin, View):
    template_name = "attendance/portal/my_attendance.html"

    def get(self, request: HttpRequest) -> HttpResponse:
        from ninefruits.person.services import CurrentStudentRecord
        from ninefruits.registration.enums import EnrollmentStatus
        from ninefruits.registration.models import Enrollment
        from ninefruits.term.models import Term

        record = CurrentStudentRecord(request.session).get(request.user)
        if record is None:
            raise Http404
        terms = list(
            Term.objects.filter(
                pk__in=Enrollment.objects.filter(student_record_id=record.pk).values("term_id")
            ).order_by("-start_date")
        )
        term_id = _int(request.GET.get("term"))
        if term_id is None or term_id not in {term.pk for term in terms}:
            today = timezone.localdate()
            started = next((term for term in terms if term.start_date <= today), None)
            chosen = started or (terms[0] if terms else None)
            term_id = chosen.pk if chosen is not None else None

        enrollments = (
            sorted(
                Enrollment.objects.filter(
                    student_record_id=record.pk,
                    term_id=term_id,
                    status__in=[EnrollmentStatus.ENROLLED, EnrollmentStatus.COMPLETED],
                ).select_related("section__course", "version"),
                key=lambda enrollment: enrollment.section.label(),
            )
            if term_id is not None
            else []
        )
        summary = AttendanceSummary()
        today = timezone.localdate()
        meetings_by_section: dict[int, list[ClassMeeting]] = {}
        for meeting in ClassMeeting.objects.filter(section_id__in=[e.section_id for e in enrollments]).order_by(
            "meeting_date", "start_time"
        ):
            meetings_by_section.setdefault(meeting.section_id, []).append(meeting)
        records: dict[tuple[int, int], AttendanceRecord] = {
            (item.enrollment_id, item.class_meeting_id): item
            for item in AttendanceRecord.objects.filter(enrollment_id__in=[e.pk for e in enrollments])
        }
        rows = []
        for enrollment in enrollments:
            held = [m for m in meetings_by_section.get(enrollment.section_id, []) if summary.is_held(m, today)]
            mine = [records[(enrollment.pk, m.pk)] for m in held if (enrollment.pk, m.pk) in records]
            rows.append(
                {
                    "enrollment": enrollment,
                    "counts": summary.counts(mine, len(held)),
                    "meetings": [{"meeting": m, "record": records.get((enrollment.pk, m.pk))} for m in held],
                }
            )
        context = {
            "title": _("My attendance"),
            "terms": terms,
            "term_id": term_id,
            "rows": rows,
            "cancelled": ClassMeetingStatus.CANCELLED,
        }
        return render(request, self.template_name, context)
