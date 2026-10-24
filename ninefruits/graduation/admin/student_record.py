""" "Degree audit" and "Waive a requirement" on a student record (original header actions of
``ViewStudentRecord``). ``StudentRecordAdmin`` mixes this in and lists ``degree_audit`` and
``waive_requirement`` in ``actions_detail``. The audit is evaluated now and shown; "Save this
audit" stores it (``RunDegreeAudits.for_record``)."""

from __future__ import annotations

from typing import Any

from django.contrib import messages
from django.core.exceptions import PermissionDenied, ValidationError
from django.http import HttpRequest, HttpResponse, HttpResponseRedirect
from django.shortcuts import get_object_or_404, render
from django.utils.translation import gettext, pgettext_lazy
from django.utils.translation import gettext_lazy as _
from unfold.decorators import action

from ninefruits.security.enums import Permission

from .forms import WaiverRequestForm


class DegreeAuditActionsMixin:
    """For ``StudentRecordAdmin`` (a ``ModelAdmin`` of ``person.StudentRecord``)."""

    def has_degree_audit_permission(self, request: HttpRequest, object_id: Any = None) -> bool:
        return object_id is not None and bool(request.user.has_perm(Permission.GRADUATION_AUDIT))

    def has_waive_requirement_permission(self, request: HttpRequest, object_id: Any = None) -> bool:
        return object_id is not None and bool(request.user.has_perm(Permission.GRADUATION_PROCESS))

    def _graduation_record(self, request: HttpRequest, object_id: Any) -> Any:
        from ninefruits.person.models import StudentRecord

        return get_object_or_404(
            StudentRecord.objects.visible_to(request.user).select_related("person", "program"), pk=object_id
        )

    @action(
        description=pgettext_lazy("graduation.actions", "Degree audit"),
        url_path="degree-audit",
        permissions=["degree_audit"],
        icon="school",
    )
    def degree_audit(self, request: HttpRequest, object_id: Any) -> HttpResponse:
        from ninefruits.graduation.actions import RunDegreeAudits
        from ninefruits.graduation.data import for_display
        from ninefruits.graduation.services import DegreeAudit
        from ninefruits.institution.admin_support import admin_url

        record = self._graduation_record(request, object_id)
        back = admin_url(record)
        if request.method == "POST":
            try:
                RunDegreeAudits().for_record(record, request.user)
            except ValidationError as error:
                for message in error.messages:
                    messages.error(request, message)
            else:
                messages.success(request, gettext("Degree audit saved."))
            return HttpResponseRedirect(back)
        results = [for_display(result.to_dict()) for result in DegreeAudit().evaluate_all(record)]
        context = {
            **self.admin_site.each_context(request),  # type: ignore[attr-defined]
            "title": pgettext_lazy("graduation.actions", "Degree audit"),
            "subtitle": f"{record.student_number} · {record.person.display_name()}",
            "results": results,
            "can_save": True,
            "opts": self.model._meta,  # type: ignore[attr-defined]
            "back_url": back,
        }
        return render(request, "graduation/admin/audit_now.html", context)

    @action(
        description=_("Waive a requirement"),
        url_path="waive-requirement",
        permissions=["waive_requirement"],
        icon="verified_user",
    )
    def waive_requirement(self, request: HttpRequest, object_id: Any) -> HttpResponse:
        from ninefruits.curriculum.models import CurriculumRequirement
        from ninefruits.graduation.actions import WaiveRequirement
        from ninefruits.institution.admin_support import admin_url, render_action_form

        record = self._graduation_record(request, object_id)
        back = admin_url(record)
        form = WaiverRequestForm(request.POST or None, record=record)
        if request.method == "POST" and form.is_valid():
            requirement = get_object_or_404(CurriculumRequirement, pk=form.cleaned_data["requirement"])
            try:
                WaiveRequirement().request(record, requirement, form.cleaned_data["reason"], request.user)
            except ValidationError as error:
                if hasattr(error, "error_dict"):
                    for field, errors in error.message_dict.items():
                        form.add_error(field if field in form.fields else None, errors)
                else:
                    form.add_error(None, error.messages)
            except PermissionDenied:
                raise
            else:
                messages.success(request, gettext("Waiver requested; it counts once another person approves it."))
                return HttpResponseRedirect(back)
        return render_action_form(
            self,
            request,
            form,
            _("Waive a requirement"),
            back,
            subtitle=f"{record.student_number} · {record.person.display_name()}",
            description=_("Another person with the graduation permission must approve the waiver before it counts."),
        )
