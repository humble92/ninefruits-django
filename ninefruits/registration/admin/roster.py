"""The section page's roster and waitlist tabs (original Filament ``RosterRelationManager`` and
``WaitlistRelationManager`` of the sections resource), mixed into ``SectionAdmin``.

- Roster (registered / capacity): every registration of the section; drop or withdraw with a
  reason; "Register a student" for staff with ``registration.manage`` covering the section.
- Waitlist (shown when the section has a waitlist size or entries): in request order; remove an
  entry with a reason; "Promote now" serves the free seats (rules checked again)."""

from __future__ import annotations

import contextvars
from typing import Any

from django.core.exceptions import PermissionDenied
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404
from django.template.loader import render_to_string
from django.urls import path, reverse
from django.utils import timezone
from django.utils.translation import gettext as gettext_now
from django.utils.translation import gettext_lazy as _
from django.utils.translation import pgettext, pgettext_lazy
from unfold.decorators import action, display

from ninefruits.registration.actions import LeaveWaitlist, PromoteWaitlist
from ninefruits.registration.enums import EnrollmentSource, EnrollmentStatus, WaitlistStatus
from ninefruits.registration.models import Enrollment, WaitlistEntry
from ninefruits.security.enums import Permission

from .common import ConfirmForm, ReasonForm, run_form
from .enrollments import staff_enroll


def _section_url(section_id: Any) -> str:
    return reverse("admin:offering_section_change", args=[section_id])


_request: contextvars.ContextVar[HttpRequest | None] = contextvars.ContextVar("section_admin_request", default=None)


def roster_rows(request: HttpRequest, section: Any) -> list[dict[str, Any]]:
    manages = section.is_registration_manageable_by(request.user)
    back = _section_url(section.pk)
    rows = []
    enrollments = (
        Enrollment.objects.visible_to(request.user)
        .filter(section_id=section.pk)
        .select_related("student_record__person", "student_record__program")
        .order_by("enrolled_at", "id")
    )
    for enrollment in enrollments:
        active = enrollment.status == EnrollmentStatus.ENROLLED and manages
        rows.append(
            {
                "student_number": enrollment.student_record.student_number,
                "name": enrollment.student_record.person.display_name(),
                "program": str(enrollment.student_record.program.name),
                "status": EnrollmentStatus(enrollment.status).label,
                "is_enrolled": enrollment.status == EnrollmentStatus.ENROLLED,
                "is_retake": enrollment.is_retake,
                "source": EnrollmentSource(enrollment.source).label,
                "enrolled_at": timezone.localtime(enrollment.enrolled_at),
                "drop_url": (
                    reverse("admin:registration_enrollment_drop_row", args=[enrollment.pk]) + f"?next={back}"
                    if active
                    else None
                ),
                "withdraw_url": (
                    reverse("admin:registration_enrollment_withdraw_row", args=[enrollment.pk]) + f"?next={back}"
                    if active
                    else None
                ),
            }
        )
    return rows


def waitlist_rows(request: HttpRequest, section: Any) -> list[dict[str, Any]]:
    manages = section.is_registration_manageable_by(request.user)
    entries = (
        WaitlistEntry.objects.visible_to(request.user)
        .filter(section_id=section.pk)
        .select_related("student_record__person")
        .order_by("requested_at", "id")
    )
    return [
        {
            "requested_at": timezone.localtime(entry.requested_at),
            "student_number": entry.student_record.student_number,
            "name": entry.student_record.person.display_name(),
            "status": WaitlistStatus(entry.status).label,
            "is_waiting": entry.status == WaitlistStatus.WAITING,
            "outcome_note": entry.outcome_note,
            "remove_url": (
                reverse("admin:offering_section_waitlist_remove", args=[section.pk, entry.pk])
                if manages and entry.status == WaitlistStatus.WAITING
                else None
            ),
        }
        for entry in entries
    ]


def has_waitlist(section: Any) -> bool:
    return bool(section.waitlist_capacity > 0 or WaitlistEntry.objects.filter(section_id=section.pk).exists())


class SectionRegistrationMixin:
    """Registration buttons of the section page."""

    registration_actions_detail = ("register_in_section", "promote_waitlist_now")
    registration_readonly_fields = ("roster_table", "waitlist_table")

    def registration_fieldsets(self, request: HttpRequest, obj: Any) -> list[Any]:
        """Roster and waitlist tabs (read only: changes go through the buttons)."""
        _request.set(request)
        if obj is None or not request.user.has_perm("view_any", Enrollment):
            return []
        fieldsets: list[Any] = [
            (
                pgettext("registration", "Roster (%(count)s / %(capacity)s)")
                % {"count": obj.enrolled_count, "capacity": obj.capacity},
                {"classes": ["tab"], "fields": ["roster_table"]},
            )
        ]
        if has_waitlist(obj):
            fieldsets.append(
                (
                    pgettext("registration.resources.waitlist", "Waitlist"),
                    {"classes": ["tab"], "fields": ["waitlist_table"]},
                )
            )
        return fieldsets

    @display(description="")
    def roster_table(self, obj: Any) -> str:
        request = _request.get()
        if request is None or obj is None or obj.pk is None:
            return ""
        return render_to_string("registration/admin/roster.html", {"rows": roster_rows(request, obj)})

    @display(description="")
    def waitlist_table(self, obj: Any) -> str:
        request = _request.get()
        if request is None or obj is None or obj.pk is None:
            return ""
        return render_to_string("registration/admin/waitlist.html", {"rows": waitlist_rows(request, obj)})

    def _registration_section(self, request: HttpRequest, object_id: Any) -> Any:
        from ninefruits.offering.models import Section

        section = get_object_or_404(Section.objects.select_related("course"), pk=object_id)
        if not section.is_registration_manageable_by(request.user):
            raise PermissionDenied
        return section

    def _manages_registration(self, request: HttpRequest, object_id: Any) -> bool:
        from ninefruits.offering.models import Section

        if object_id is None:
            return bool(request.user.has_perm(Permission.REGISTRATION_MANAGE))
        section = Section.objects.filter(pk=object_id).first()
        return section is not None and section.is_registration_manageable_by(request.user)

    def has_register_in_section_permission(self, request: HttpRequest, object_id: Any = None) -> bool:
        return self._manages_registration(request, object_id)

    @action(
        description=pgettext_lazy("registration", "Register a student"),
        url_path="register-student",
        permissions=["register_in_section"],
        icon="add_circle",
    )
    def register_in_section(self, request: HttpRequest, object_id: Any) -> HttpResponse:
        section = self._registration_section(request, object_id)
        return staff_enroll(self, request, _section_url(section.pk), section=section)

    def has_promote_waitlist_now_permission(self, request: HttpRequest, object_id: Any = None) -> bool:
        from ninefruits.offering.models import Section

        if not self._manages_registration(request, object_id):
            return False
        section = Section.objects.filter(pk=object_id).first() if object_id is not None else None
        return section is None or has_waitlist(section)

    @action(
        description=_("Promote now"), url_path="promote-waitlist", permissions=["promote_waitlist_now"], icon="upgrade"
    )
    def promote_waitlist_now(self, request: HttpRequest, object_id: Any) -> HttpResponse:
        section = self._registration_section(request, object_id)
        form = ConfirmForm(request.POST if request.method == "POST" else None)

        def perform(form: Any) -> str:
            counts = PromoteWaitlist().handle(section)
            return gettext_now("Promoted %(promoted)s, removed %(removed)s, expired %(expired)s.") % counts

        return run_form(
            self, request, form, _("Promote now"), _section_url(section.pk), perform, subtitle=section.label()
        )

    def remove_from_waitlist(self, request: HttpRequest, section_id: int, entry_id: int) -> HttpResponse:
        section = self._registration_section(request, section_id)
        entry = get_object_or_404(
            WaitlistEntry.objects.visible_to(request.user).select_related("student_record", "section"),
            pk=entry_id,
            section=section,
        )
        form = ReasonForm(request.POST or None)

        def perform(form: Any) -> None:
            LeaveWaitlist().handle(entry, request.user, form.cleaned_data["reason"])

        return run_form(
            self,
            request,
            form,
            pgettext("registration", "Remove"),
            _section_url(section.pk),
            perform,
            subtitle=f"{section.label()} · {entry.student_record.student_number}",
        )

    def get_urls(self) -> list[Any]:
        info = self.model._meta.app_label, self.model._meta.model_name  # type: ignore[attr-defined]
        view = self.admin_site.admin_view(self.remove_from_waitlist)  # type: ignore[attr-defined]
        return [
            path("<int:section_id>/waitlist/<int:entry_id>/remove/", view, name="{}_{}_waitlist_remove".format(*info)),
            *super().get_urls(),  # type: ignore[misc]
        ]
