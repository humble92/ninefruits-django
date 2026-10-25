"""Registrations (original Filament ``Resources/Registration/Enrollments``): the term's
registrations of records the user can see and of sections in their scope, staff registration
with waived rules, and drop or withdraw with a reason. Rows change only through the actions."""

from __future__ import annotations

from typing import Any

from django.contrib import admin
from django.contrib.admin.options import ActionLocation
from django.core.exceptions import PermissionDenied
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404
from django.urls import reverse
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _
from django.utils.translation import pgettext, pgettext_lazy
from unfold.decorators import action, display

from ninefruits.adminpanel.mixins import CatalogAdmin
from ninefruits.adminpanel.navigation import NavigationGroup
from ninefruits.person.models import Person
from ninefruits.registration.actions import DropEnrollment, EnrollStudent
from ninefruits.registration.data import EnrollOptions
from ninefruits.registration.enums import EnrollmentSource, EnrollmentStatus
from ninefruits.registration.models import Enrollment
from ninefruits.security.enums import Permission

from .common import ChoiceFilter, DefaultTermFilter, ReasonForm, StaffEnrollForm, report_outcome, run_form


class EnrollmentStatusFilter(ChoiceFilter):
    title = pgettext_lazy("registration", "Status")
    parameter_name = "status"
    choices_class = EnrollmentStatus
    default = EnrollmentStatus.ENROLLED.value


def staff_enroll(model_admin: Any, request: HttpRequest, back_url: str, section: Any = None) -> HttpResponse:
    """The "Register a student" form (also on the section's roster tab)."""
    if not request.user.has_perm(Permission.REGISTRATION_MANAGE):
        raise PermissionDenied
    form = StaffEnrollForm(request.POST or None, user=request.user, section=section)

    def perform(form: Any) -> None:
        outcome = EnrollStudent().handle(
            form.cleaned_data["student_number"],
            form.chosen_section(),
            request.user,
            EnrollOptions(
                waitlist_if_full=bool(form.cleaned_data.get("waitlist")),
                waive=form.waived(),
                reason=form.cleaned_data["reason"],
            ),
        )
        report_outcome(request, outcome)

    title = pgettext("registration", "Register a student")
    subtitle = section.label() if section is not None else None
    return run_form(model_admin, request, form, title, back_url, perform, subtitle=subtitle)


def end_enrollment(
    model_admin: Any, request: HttpRequest, enrollment: Enrollment, kind: str, back_url: str
) -> HttpResponse:
    """Drop or withdraw with a reason (staff, at any time)."""
    if enrollment.status != EnrollmentStatus.ENROLLED or not request.user.has_perm("update", enrollment):
        raise PermissionDenied
    form = ReasonForm(request.POST or None)

    def perform(form: Any) -> str:
        end = DropEnrollment()
        if kind == "drop":
            end.drop(enrollment, request.user, form.cleaned_data["reason"])
            return str(_("Dropped."))
        end.withdraw(enrollment, request.user, form.cleaned_data["reason"])
        return str(_("Withdrawn."))

    title = pgettext("registration.actions", "Drop") if kind == "drop" else pgettext("registration.actions", "Withdraw")
    subtitle = f"{enrollment.student_record.student_number} · {enrollment.section.label()}"
    return run_form(model_admin, request, form, title, back_url, perform, subtitle=subtitle)


@admin.register(Enrollment)
class EnrollmentAdmin(CatalogAdmin):
    permissions = {"view": Permission.ENROLLMENTS_VIEW, "change": Permission.REGISTRATION_MANAGE}
    navigation_group = NavigationGroup.REGISTRATION
    navigation_icon = "assignment"
    navigation_order = 10
    list_display = (
        "student_number",
        "name",
        "section_link",
        "title",
        "credits",
        "status_badge",
        "is_retake",
        "source_label",
        "enrolled_at",
    )
    list_filter = (DefaultTermFilter, EnrollmentStatusFilter)
    search_fields = ("student_record__student_number",)
    list_select_related = ("student_record__person", "section__course", "version")
    ordering = ("-enrolled_at", "-id")
    list_per_page = 50
    actions_list = ("register_student",)
    actions_row = ("drop_row", "withdraw_row")

    # -- access ----------------------------------------------------------------------------------
    def has_view_permission(self, request: HttpRequest, obj: Any = None) -> bool:
        return self.policy_allows(request, "view_any", Enrollment)

    def has_add_permission(self, request: HttpRequest, *args: Any) -> bool:
        return False

    def has_change_permission(self, request: HttpRequest, obj: Any = None) -> bool:
        return False

    def has_delete_permission(self, request: HttpRequest, obj: Any = None) -> bool:
        return False

    def get_actions(self, request: HttpRequest, action_location: Any = ActionLocation.CHANGE_LIST) -> dict[str, Any]:
        actions = super().get_actions(request, action_location)
        actions.pop("delete_selected", None)
        return actions

    def get_search_results(self, request: HttpRequest, queryset: Any, search_term: str) -> tuple[Any, bool]:
        term = search_term.strip()
        if not term:
            return queryset, False
        people = Person.objects.search(term).values("pk")
        return (
            queryset.filter(student_record__student_number__icontains=term)
            | queryset.filter(student_record__person__in=people),
            False,
        )

    # -- columns ---------------------------------------------------------------------------------
    @display(description=_("Student number"), ordering="student_record__student_number")
    def student_number(self, obj: Enrollment) -> str:
        return obj.student_record.student_number

    @display(description=pgettext_lazy("people", "Name"))
    def name(self, obj: Enrollment) -> str:
        return obj.student_record.person.display_name()

    @display(description=pgettext_lazy("offering", "Section"))
    def section_link(self, obj: Enrollment) -> Any:
        user = getattr(self, "_request_user", None)
        if user is not None and obj.section.is_manageable_by(user):
            url = reverse("admin:offering_section_change", args=[obj.section_id])
            return format_html('<a class="underline" href="{}">{}</a>', url, obj.section.label())
        return obj.section.label()

    @display(description=pgettext_lazy("curriculum", "Title"))
    def title(self, obj: Enrollment) -> str:
        return str(obj.version.title or "")

    @display(
        description=pgettext_lazy("registration", "Status"),
        label={
            EnrollmentStatus.ENROLLED.label: "success",
            EnrollmentStatus.COMPLETED.label: "info",
        },
    )
    def status_badge(self, obj: Enrollment) -> str:
        return str(EnrollmentStatus(obj.status).label)

    @display(description=pgettext_lazy("registration", "Source"))
    def source_label(self, obj: Enrollment) -> str:
        return str(EnrollmentSource(obj.source).label)

    def changelist_view(self, request: HttpRequest, extra_context: dict[str, Any] | None = None) -> Any:
        self._request_user = request.user
        return super().changelist_view(request, extra_context)

    # -- actions ---------------------------------------------------------------------------------
    def has_register_student_permission(self, request: HttpRequest) -> bool:
        return self.policy_allows(request, "create", Enrollment)

    @action(
        description=pgettext_lazy("registration", "Register a student"),
        url_path="register-student",
        permissions=["register_student"],
        icon="add_circle",
    )
    def register_student(self, request: HttpRequest) -> HttpResponse:
        return staff_enroll(self, request, reverse("admin:registration_enrollment_changelist"))

    def has_drop_row_permission(self, request: HttpRequest, object_id: Any = None) -> bool:
        return bool(request.user.has_perm(Permission.REGISTRATION_MANAGE))

    def _enrollment(self, request: HttpRequest, object_id: Any) -> Enrollment:
        enrollment: Enrollment = get_object_or_404(
            self.get_queryset(request).select_related("section__course", "student_record"), pk=object_id
        )
        return enrollment

    @action(
        description=pgettext_lazy("registration.actions", "Drop"),
        url_path="drop",
        permissions=["drop_row"],
        icon="remove_circle",
    )
    def drop_row(self, request: HttpRequest, object_id: Any) -> HttpResponse:
        back = reverse("admin:registration_enrollment_changelist")
        return end_enrollment(self, request, self._enrollment(request, object_id), "drop", back)

    @action(
        description=pgettext_lazy("registration.actions", "Withdraw"),
        url_path="withdraw",
        permissions=["drop_row"],
        icon="logout",
    )
    def withdraw_row(self, request: HttpRequest, object_id: Any) -> HttpResponse:
        back = reverse("admin:registration_enrollment_changelist")
        return end_enrollment(self, request, self._enrollment(request, object_id), "withdraw", back)
