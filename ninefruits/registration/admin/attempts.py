"""Registration attempt log (original Filament ``Resources/Registration/Attempts``): every attempt
with the rules not met, read only. Filter by term, outcome and action; search by student
number."""

from __future__ import annotations

from typing import Any

from django.contrib import admin
from django.contrib.admin.options import ActionLocation
from django.http import HttpRequest
from django.utils.html import format_html_join
from django.utils.translation import gettext_lazy as _
from django.utils.translation import pgettext_lazy
from unfold.decorators import display

from ninefruits.adminpanel.mixins import ReadOnlyCatalogAdmin
from ninefruits.adminpanel.navigation import NavigationGroup
from ninefruits.registration.enums import AttemptAction, AttemptOutcome
from ninefruits.registration.models import RegistrationAttempt
from ninefruits.security.enums import Permission

from .common import AnyTermFilter, ChoiceFilter


class OutcomeFilter(ChoiceFilter):
    title = _("Outcome")
    parameter_name = "outcome"
    choices_class = AttemptOutcome


class ActionFilter(ChoiceFilter):
    title = _("Action")
    parameter_name = "action"
    choices_class = AttemptAction


@admin.register(RegistrationAttempt)
class RegistrationAttemptAdmin(ReadOnlyCatalogAdmin):
    permissions = {"view": Permission.ENROLLMENTS_VIEW}
    navigation_group = NavigationGroup.REGISTRATION
    navigation_icon = "list"
    navigation_order = 60
    list_display = (
        "attempted_at_seconds",
        "student_number",
        "section_label",
        "action_label",
        "outcome_badge",
        "failed_rules",
        "actor_email",
        "request_id",
    )
    list_filter = (AnyTermFilter, OutcomeFilter, ActionFilter)
    search_fields = ("student_record__student_number",)
    list_select_related = ("student_record", "section__course", "actor")
    ordering = ("-attempted_at", "-id")
    list_per_page = 50

    def has_view_permission(self, request: HttpRequest, obj: Any = None) -> bool:
        return self.policy_allows(request, "view_any", RegistrationAttempt)

    def get_actions(self, request: HttpRequest, action_location: Any = ActionLocation.CHANGE_LIST) -> dict[str, Any]:
        actions = super().get_actions(request, action_location)
        actions.pop("delete_selected", None)
        return actions

    @display(description=pgettext_lazy("registration", "Time"), ordering="attempted_at")
    def attempted_at_seconds(self, obj: RegistrationAttempt) -> str:
        from django.utils import timezone

        return timezone.localtime(obj.attempted_at).strftime("%Y-%m-%d %H:%M:%S")

    @display(description=_("Student number"), ordering="student_record__student_number")
    def student_number(self, obj: RegistrationAttempt) -> str:
        return obj.student_record.student_number

    @display(description=pgettext_lazy("offering", "Section"))
    def section_label(self, obj: RegistrationAttempt) -> str:
        return obj.section.label() if obj.section else "-"

    @display(description=_("Action"))
    def action_label(self, obj: RegistrationAttempt) -> str:
        return str(AttemptAction(obj.action).label)

    @display(
        description=_("Outcome"),
        label={
            AttemptOutcome.SUCCEEDED.label: "success",
            AttemptOutcome.WAITLISTED.label: "info",
            AttemptOutcome.REFUSED.label: "danger",
        },
    )
    def outcome_badge(self, obj: RegistrationAttempt) -> str:
        return str(AttemptOutcome(obj.outcome).label)

    @display(description=_("Rules not met"))
    def failed_rules(self, obj: RegistrationAttempt) -> Any:
        lines = obj.failed_summary().splitlines()
        return format_html_join("", "<div>{}</div>", ((line,) for line in lines)) if lines else "-"

    @display(description=_("By"))
    def actor_email(self, obj: RegistrationAttempt) -> str:
        return obj.actor.email if obj.actor else "-"
