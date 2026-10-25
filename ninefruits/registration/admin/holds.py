"""Holds and rule overrides (original Filament ``Resources/Registration/Holds`` and
``Overrides``): list of records the user can see (in force by default), place a hold, release
it with a reason, import holds from CSV, grant and revoke overrides. Never deleted."""

from __future__ import annotations

from typing import Any

from django.contrib import admin
from django.contrib.admin.options import ActionLocation
from django.core.exceptions import PermissionDenied
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404
from django.urls import reverse
from django.utils.text import Truncator
from django.utils.translation import gettext_lazy as _
from django.utils.translation import pgettext_lazy
from unfold.decorators import action, display

from ninefruits.adminpanel.navigation import NavigationGroup
from ninefruits.institution.admin_support import ReferenceAdmin
from ninefruits.person.models import Person
from ninefruits.registration.actions import ManageHolds
from ninefruits.registration.enums import HoldType, RuleCode
from ninefruits.registration.models import RegistrationHold, RegistrationOverride
from ninefruits.security.enums import Permission
from ninefruits.term.models import Term

from .common import (
    AnyTermFilter,
    ChoiceFilter,
    ConfirmForm,
    GrantOverrideForm,
    InForceFilter,
    PlaceHoldForm,
    ReasonForm,
    run_form,
)


class _StudentListMixin:
    """List columns and search of rows that belong to a student record."""

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

    def get_actions(self, request: HttpRequest, action_location: Any = ActionLocation.CHANGE_LIST) -> dict[str, Any]:
        actions: dict[str, Any] = super().get_actions(request, action_location)  # type: ignore[misc]
        actions.pop("delete_selected", None)
        return actions

    def has_add_permission(self, request: HttpRequest, *args: Any) -> bool:
        return False

    def has_change_permission(self, request: HttpRequest, obj: Any = None) -> bool:
        return False

    def has_delete_permission(self, request: HttpRequest, obj: Any = None) -> bool:
        return False

    @display(description=_("Student number"), ordering="student_record__student_number")
    def student_number(self, obj: Any) -> str:
        return str(obj.student_record.student_number)

    @display(description=pgettext_lazy("people", "Name"))
    def name(self, obj: Any) -> str:
        return str(obj.student_record.person.display_name())

    @display(description=pgettext_lazy("common", "Reason"))
    def reason_short(self, obj: Any) -> str:
        return Truncator(obj.reason).chars(40)


class HoldTypeFilter(ChoiceFilter):
    title = _("Hold type")
    parameter_name = "hold_type"
    choices_class = HoldType


@admin.register(RegistrationHold)
class RegistrationHoldAdmin(_StudentListMixin, ReferenceAdmin):
    permissions = {"view": Permission.REGISTRATION_MANAGE, "change": Permission.REGISTRATION_HOLDS_MANAGE}
    navigation_group = NavigationGroup.REGISTRATION
    navigation_icon = "block"
    navigation_order = 20
    translated_search_fields = ()
    import_type = "registration_holds"
    list_display = (
        "student_number",
        "name",
        "type_badge",
        "blocks_registration",
        "reason_short",
        "starts_at",
        "ends_at",
        "released_at",
    )
    list_filter = (InForceFilter, HoldTypeFilter)
    search_fields = ("student_record__student_number",)
    list_select_related = ("student_record__person",)
    ordering = ("-starts_at", "-id")
    actions_list = ("place_hold", "import_csv")
    actions_row = ("release_row",)

    def has_view_permission(self, request: HttpRequest, obj: Any = None) -> bool:
        return self.policy_allows(request, "view_any", RegistrationHold)

    @display(description=_("Hold type"), label=True)
    def type_badge(self, obj: RegistrationHold) -> str:
        return str(HoldType(obj.hold_type).label)

    def has_place_hold_permission(self, request: HttpRequest) -> bool:
        return self.policy_allows(request, "create", RegistrationHold)

    @action(description=_("Place a hold"), url_path="place", permissions=["place_hold"], icon="block")
    def place_hold(self, request: HttpRequest) -> HttpResponse:
        form = PlaceHoldForm(request.POST or None, user=request.user)

        def perform(form: Any) -> str:
            data = form.cleaned_data
            ManageHolds().place(
                data["student_number"],
                HoldType(data["hold_type"]),
                data["reason"],
                request.user,
                blocks_registration=bool(data.get("blocks_registration")),
                blocks_grades=bool(data.get("blocks_grades")),
                blocks_certificates=bool(data.get("blocks_certificates")),
                starts_at=data.get("starts_at"),
                ends_at=data.get("ends_at"),
            )
            return str(_("Place a hold"))

        return run_form(self, request, form, _("Place a hold"), self._changelist_url(), perform)

    def has_release_row_permission(self, request: HttpRequest, object_id: Any = None) -> bool:
        return bool(request.user.has_perm(Permission.REGISTRATION_HOLDS_MANAGE))

    @action(description=_("Release"), url_path="release", permissions=["release_row"], icon="lock_open")
    def release_row(self, request: HttpRequest, object_id: Any) -> HttpResponse:
        hold = get_object_or_404(self.get_queryset(request).select_related("student_record"), pk=object_id)
        if hold.released_at is not None or not request.user.has_perm("update", hold):
            raise PermissionDenied
        form = ReasonForm(request.POST or None)

        def perform(form: Any) -> None:
            ManageHolds().release(hold, form.cleaned_data["reason"], request.user)

        return run_form(
            self,
            request,
            form,
            _("Release"),
            self._changelist_url(),
            perform,
            subtitle=hold.student_record.student_number,
        )


class OverrideTermFilter(AnyTermFilter):
    pass


@admin.register(RegistrationOverride)
class RegistrationOverrideAdmin(_StudentListMixin, ReferenceAdmin):
    permissions = {"view": Permission.REGISTRATION_MANAGE, "change": Permission.REGISTRATION_HOLDS_MANAGE}
    navigation_group = NavigationGroup.REGISTRATION
    navigation_icon = "verified_user"
    navigation_order = 30
    translated_search_fields = ()
    list_display = (
        "student_number",
        "name",
        "term_name",
        "rule_badge",
        "limit",
        "reason_short",
        "expires_at",
        "revoked_at",
        "granted_at",
    )
    list_filter = (OverrideTermFilter, InForceFilter)
    search_fields = ("student_record__student_number",)
    list_select_related = ("student_record__person", "term", "section__course", "course")
    ordering = ("-created_at", "-id")
    actions_list = ("grant_override",)
    actions_row = ("revoke_row",)

    def has_view_permission(self, request: HttpRequest, obj: Any = None) -> bool:
        return self.policy_allows(request, "view_any", RegistrationOverride)

    @display(description=_("term"))
    def term_name(self, obj: RegistrationOverride) -> str:
        return str(obj.term.name)

    @display(description=_("Rule"), label=True)
    def rule_badge(self, obj: RegistrationOverride) -> str:
        return str(RuleCode(obj.rule_code).label)

    @display(description=_("Applies to"))
    def limit(self, obj: RegistrationOverride) -> str:
        if obj.section is not None:
            return obj.section.label()
        if obj.course is not None:
            return obj.course.code
        return str(_("Whole term"))

    @display(description=_("Granted"), ordering="created_at")
    def granted_at(self, obj: RegistrationOverride) -> Any:
        return obj.created_at

    def has_grant_override_permission(self, request: HttpRequest) -> bool:
        return self.policy_allows(request, "create", RegistrationOverride)

    @action(description=_("Grant an override"), url_path="grant", permissions=["grant_override"], icon="verified_user")
    def grant_override(self, request: HttpRequest) -> HttpResponse:
        form = GrantOverrideForm(request.POST or None, user=request.user)

        def perform(form: Any) -> str:
            data = form.cleaned_data
            section, course = data.get("section_obj"), data.get("course_obj")
            ManageHolds().grant_override(
                data["student_number"],
                get_object_or_404(Term, pk=data["term_id"]),
                RuleCode(data["rule_code"]),
                data["reason"],
                request.user,
                section_id=section.pk if section is not None else None,
                course_id=course.pk if course is not None and section is None else None,
                expires_at=data.get("expires_at"),
            )
            return str(_("Grant an override"))

        return run_form(self, request, form, _("Grant an override"), self._changelist_url(), perform)

    def has_revoke_row_permission(self, request: HttpRequest, object_id: Any = None) -> bool:
        return bool(request.user.has_perm(Permission.REGISTRATION_HOLDS_MANAGE))

    @action(
        description=pgettext_lazy("registration", "Revoke"),
        url_path="revoke",
        permissions=["revoke_row"],
        icon="cancel",
    )
    def revoke_row(self, request: HttpRequest, object_id: Any) -> HttpResponse:
        override = get_object_or_404(self.get_queryset(request).select_related("student_record"), pk=object_id)
        if override.revoked_at is not None or not request.user.has_perm("update", override):
            raise PermissionDenied
        form = ConfirmForm(request.POST if request.method == "POST" else None)

        def perform(form: Any) -> None:
            ManageHolds().revoke_override(override, request.user)

        return run_form(
            self,
            request,
            form,
            pgettext_lazy("registration", "Revoke"),
            reverse("admin:registration_registrationoverride_changelist"),
            perform,
            subtitle=f"{override.student_record.student_number} · {RuleCode(override.rule_code).label}",
        )
