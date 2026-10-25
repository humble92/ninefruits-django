"""Users, roles and role assignments in the admin panel (original Filament
``Resources/Users`` with ``RoleAssignmentsRelationManager`` and ``Resources/Roles``).

Business rules stay in the actions: editing an account goes through ``UpdateUserAccount``,
assignments through ``AssignRole``/``RevokeRoleAssignment``, role permissions through
``UpdateRolePermissions``. Assignments are never edited: they are ended and new ones created."""

from __future__ import annotations

import re
import secrets
from datetime import datetime
from typing import Any, ClassVar

from django import forms
from django.contrib import admin, messages
from django.core.exceptions import PermissionDenied, ValidationError
from django.db.models import Count, Q
from django.http import HttpRequest, HttpResponse, HttpResponseRedirect
from django.shortcuts import get_object_or_404, render
from django.urls import path, reverse
from django.utils import timezone
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _
from django.utils.translation import pgettext_lazy
from unfold.admin import TabularInline
from unfold.decorators import action, display
from unfold.enums import ActionVariant
from unfold.forms import BaseDialogForm
from unfold.widgets import (
    UnfoldAdminCheckboxSelectMultipleWidget,
    UnfoldAdminSelectWidget,
    UnfoldAdminSplitDateTimeWidget,
    UnfoldAdminTextareaWidget,
    UnfoldAdminTextInputWidget,
)

from ninefruits.adminpanel.mixins import CatalogAdmin, CatalogPermissionMixin
from ninefruits.adminpanel.navigation import NavigationGroup
from ninefruits.security.actions import (
    AssignRole,
    ResetUserMfa,
    RevokeRoleAssignment,
    UnlockUser,
    UpdateRolePermissions,
    UpdateUserAccount,
)
from ninefruits.security.enums import Permission, Persona, ScopeType
from ninefruits.security.models import GUARD_NAME, Role, RoleAssignment, User
from ninefruits.security.services.mfa_policy import MfaPolicy

REASON_LABEL = pgettext_lazy("common", "Reason")


def _reason_field() -> forms.CharField:
    return forms.CharField(label=REASON_LABEL, max_length=1000, widget=UnfoldAdminTextareaWidget(attrs={"rows": 3}))


def _locale_choices() -> list[tuple[str, str]]:
    from ninefruits.institution.services.supported_locales import SupportedLocales

    return [("", "-"), *((code, SupportedLocales.label(code)) for code in SupportedLocales().all())]


# -- users ---------------------------------------------------------------------------------------
class UserAdminForm(forms.ModelForm):  # type: ignore[type-arg]
    locale = forms.ChoiceField(label=_("Language"), required=False, widget=UnfoldAdminSelectWidget)

    class Meta:
        model = User
        fields = ("name", "email", "locale", "is_active")
        labels = {"name": _("Name"), "email": pgettext_lazy("authentication", "Email"), "is_active": _("Active")}
        help_texts = {
            "name": _(
                "Used only for accounts without a person (e.g. service accounts). "
                "Linked accounts show the person's name."
            )
        }

    actor: User | None = None

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.fields["locale"].choices = _locale_choices()  # type: ignore[attr-defined]
        self.fields["email"].widget = forms.EmailInput(attrs={"class": UnfoldAdminTextInputWidget().attrs["class"]})
        self.fields["name"].required = self.instance.person_id is None

    def clean_email(self) -> str:
        email = str(self.cleaned_data["email"]).strip().lower()
        if User.objects.filter(email=email).exclude(pk=self.instance.pk).exists():
            raise ValidationError(_("The email has already been taken."))
        return email

    def clean_locale(self) -> str | None:
        return self.cleaned_data.get("locale") or None

    def clean(self) -> dict[str, Any]:
        cleaned = super().clean() or {}
        if self.instance.pk and self.actor is not None:
            try:
                UpdateUserAccount._guard(self.instance, cleaned, self.actor)
            except ValidationError as error:
                for field, errors in error.message_dict.items():
                    self.add_error(field if field in self.fields else None, errors)
        return cleaned


class ReasonDialogForm(BaseDialogForm):
    reason = _reason_field()


class ReasonForm(forms.Form):
    reason = _reason_field()


class AssignRoleForm(forms.Form):
    role = forms.ModelChoiceField(
        label=_("Role"), queryset=Role.objects.none(), widget=UnfoldAdminSelectWidget, empty_label=None
    )
    scope_type = forms.ChoiceField(
        label=_("Scope"), choices=(), initial=ScopeType.GLOBAL.value, widget=UnfoldAdminSelectWidget
    )
    # Querysets are set in __init__ (organization models load after this app).
    scope_org_unit: forms.ModelChoiceField[Any] = forms.ModelChoiceField(
        label=_("Scope target"),
        queryset=None,
        required=False,
        help_text=_("Includes all units below the selected ones."),
        widget=UnfoldAdminSelectWidget,
    )
    scope_program: forms.ModelChoiceField[Any] = forms.ModelChoiceField(
        label=_("Scope target"), queryset=None, required=False, widget=UnfoldAdminSelectWidget
    )
    starts_at = forms.SplitDateTimeField(label=_("Starts"), required=False, widget=UnfoldAdminSplitDateTimeWidget)
    ends_at = forms.SplitDateTimeField(label=_("Ends"), required=False, widget=UnfoldAdminSplitDateTimeWidget)
    reason = _reason_field()

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.fields["role"].queryset = Role.objects.assignable()  # type: ignore[attr-defined]
        self.fields["scope_type"].choices = ScopeType.choices()  # type: ignore[attr-defined]
        from ninefruits.organization.models import OrgUnit, Program

        self.fields["scope_org_unit"].queryset = OrgUnit.objects.order_by("code")  # type: ignore[attr-defined]
        self.fields["scope_program"].queryset = Program.objects.order_by("code")  # type: ignore[attr-defined]

    def clean(self) -> dict[str, Any]:
        cleaned = super().clean() or {}
        starts_at, ends_at = cleaned.get("starts_at"), cleaned.get("ends_at")
        if starts_at and ends_at and ends_at <= starts_at:
            self.add_error("ends_at", _("The end must be after the start."))
        scope_type = cleaned.get("scope_type")
        target = {
            ScopeType.ORG_UNIT.value: ("scope_org_unit", cleaned.get("scope_org_unit")),
            ScopeType.PROGRAM.value: ("scope_program", cleaned.get("scope_program")),
        }.get(str(scope_type))
        cleaned["scope_id"] = None
        if target is not None:
            field, value = target
            if value is None:
                self.add_error(
                    field, _("Choose a scope target for scoped assignments, and none for global assignments.")
                )
            else:
                cleaned["scope_id"] = value.pk
        return cleaned


class RoleAssignmentInline(CatalogPermissionMixin, TabularInline):
    model = RoleAssignment
    fk_name = "user"
    extra = 0
    can_delete = False
    show_change_link = False
    verbose_name = _("Role assignment")
    verbose_name_plural = _("Role assignments")
    permissions: ClassVar[dict[str, str]] = {"view": Permission.USERS_VIEW}
    fields = ("role", "scope_display", "starts_at", "ends_at", "active_display", "reason", "assigned_by", "end_link")
    readonly_fields = fields

    def has_add_permission(self, request: HttpRequest, obj: Any = None) -> bool:
        return False

    def has_change_permission(self, request: HttpRequest, obj: Any = None) -> bool:
        return False

    def get_queryset(self, request: HttpRequest) -> Any:
        return super().get_queryset(request).select_related("role", "assigned_by")

    @admin.display(description=_("Scope"))
    def scope_display(self, obj: RoleAssignment) -> str:
        return obj.describe_scope()

    @display(description=_("Active"), boolean=True)
    def active_display(self, obj: RoleAssignment) -> bool:
        return obj.is_active()

    @admin.display(description="")
    def end_link(self, obj: RoleAssignment) -> str:
        request = getattr(self, "_request", None)
        if request is None or not request.user.has_perm("revoke", obj):
            return ""
        url = reverse("admin:security_user_revoke_assignment", args=[obj.user_id, obj.pk])
        return format_html('<a href="{}" class="text-red-600 underline">{}</a>', url, _("End assignment"))

    def get_formset(self, request: HttpRequest, obj: Any = None, **kwargs: Any) -> Any:
        self._request = request
        return super().get_formset(request, obj, **kwargs)


@admin.register(User)
class UserAdmin(CatalogAdmin):
    permissions: ClassVar[dict[str, str]] = {
        "view": Permission.USERS_VIEW,
        "add": Permission.USERS_CREATE,
        "change": Permission.USERS_UPDATE,
    }
    navigation_group = NavigationGroup.ACCESS
    navigation_icon = "group"
    navigation_label = pgettext_lazy("admin", "Users")
    navigation_order = 10
    form = UserAdminForm
    list_display = ("display_name_column", "email", "is_active", "mfa_enrolled", "last_login")
    list_filter = ("is_active",)
    search_fields = ("name", "email")
    ordering = ("name", "email")
    readonly_fields = ("mfa_enrolled", "last_login", "linked_person")
    inlines = (RoleAssignmentInline,)
    actions_detail = ("assign_role", "reset_mfa", "unlock")

    def get_fields(self, request: HttpRequest, obj: Any = None) -> Any:
        if obj is None:
            return ("name", "email", "locale")
        return ("name", "email", "locale", "is_active", "linked_person", "mfa_enrolled", "last_login")

    def get_inlines(self, request: HttpRequest, obj: Any) -> Any:
        return self.inlines if obj is not None else ()

    def get_form(self, request: HttpRequest, obj: Any = None, change: bool = False, **kwargs: Any) -> Any:
        form: Any = super().get_form(request, obj, change, **kwargs)
        form.actor = request.user
        return form

    def has_delete_permission(self, request: HttpRequest, obj: Any = None) -> bool:
        """Accounts are deactivated, not deleted, so their history stays attached."""
        return False

    @display(description=_("Name"), ordering="name")
    def display_name_column(self, obj: User) -> str:
        return obj.display_name()

    @display(description=_("Two-factor"), boolean=True)
    def mfa_enrolled(self, obj: User) -> bool:
        return MfaPolicy().is_enrolled(obj)

    @admin.display(description=_("Linked person"))
    def linked_person(self, obj: User) -> str:
        return str(_("Yes")) if obj.person_id is not None else str(_("None"))

    def save_model(self, request: HttpRequest, obj: User, form: Any, change: bool) -> None:
        if not change:
            # New accounts get a random password and a password reset link by email.
            obj.set_password(secrets.token_urlsafe(32))
            obj.email = obj.email.lower()
            obj.save()
            _send_password_reset_link(request, obj)
            return
        data = {name: form.cleaned_data[name] for name in UpdateUserAccount.EDITABLE if name in form.cleaned_data}
        original = User.objects.get(pk=obj.pk)
        for name in data:
            setattr(obj, name, getattr(original, name))
        UpdateUserAccount()(obj, data, request.user)  # type: ignore[arg-type]

    # -- detail actions (original ViewUser header actions and the relation manager) ------------
    def _target(self, object_id: Any) -> User:
        return get_object_or_404(User, pk=object_id)

    def has_reset_mfa_permission(self, request: HttpRequest, object_id: Any = None) -> bool:
        return object_id is not None and request.user.has_perm("reset_mfa", self._target(object_id))

    def has_unlock_permission(self, request: HttpRequest, object_id: Any = None) -> bool:
        return object_id is not None and request.user.has_perm("unlock", self._target(object_id))

    def has_assign_role_permission(self, request: HttpRequest, object_id: Any = None) -> bool:
        return self.policy_allows(request, "create", RoleAssignment)

    @action(
        description=_("Reset two-factor authentication"),
        url_path="reset-mfa",
        permissions=["reset_mfa"],
        variant=ActionVariant.DANGER,
        icon="key",
        dialog={"title": _("Reset two-factor authentication"), "form_class": ReasonDialogForm},
    )
    def reset_mfa(self, request: HttpRequest, form: ReasonDialogForm, object_id: Any) -> HttpResponse:
        user = self._target(object_id)
        ResetUserMfa()(user, form.cleaned_data["reason"], request.user)  # type: ignore[arg-type]
        messages.success(request, _("Two-factor authentication was reset."))
        return HttpResponseRedirect(reverse("admin:security_user_change", args=[user.pk]))

    @action(
        description=_("Unlock sign-in"),
        url_path="unlock",
        permissions=["unlock"],
        icon="lock_open",
        dialog={"title": _("Unlock sign-in"), "form_class": ReasonDialogForm},
    )
    def unlock(self, request: HttpRequest, form: ReasonDialogForm, object_id: Any) -> HttpResponse:
        user = self._target(object_id)
        UnlockUser()(user, form.cleaned_data["reason"], request.user)  # type: ignore[arg-type]
        messages.success(request, _("Sign-in unlocked."))
        return HttpResponseRedirect(reverse("admin:security_user_change", args=[user.pk]))

    @action(description=_("Assign role"), url_path="assign-role", permissions=["assign_role"], icon="badge")
    def assign_role(self, request: HttpRequest, object_id: Any) -> HttpResponse:
        user = self._target(object_id)
        form = AssignRoleForm(request.POST or None)
        if request.method == "POST" and form.is_valid():
            data = form.cleaned_data
            try:
                AssignRole()(
                    user,
                    data["role"],
                    data["reason"],
                    ScopeType(data["scope_type"]),
                    data.get("scope_id"),
                    _aware(data.get("starts_at")),
                    _aware(data.get("ends_at")),
                    request.user,  # type: ignore[arg-type]
                )
            except ValidationError as error:
                for field, errors in error.message_dict.items():
                    form.add_error(field if field in form.fields else None, errors)
            else:
                messages.success(request, _("Role assigned."))
                return HttpResponseRedirect(reverse("admin:security_user_change", args=[user.pk]))
        return self._render_form(request, user, form, _("Assign role"))

    def get_urls(self) -> list[Any]:
        return [
            path(
                "<int:user_id>/assignments/<int:assignment_id>/revoke/",
                self.admin_site.admin_view(self.revoke_assignment_view),
                name="security_user_revoke_assignment",
            ),
            *super().get_urls(),
        ]

    def revoke_assignment_view(self, request: HttpRequest, user_id: int, assignment_id: int) -> HttpResponse:
        assignment = get_object_or_404(RoleAssignment, pk=assignment_id, user_id=user_id)
        if not request.user.has_perm("revoke", assignment):
            raise PermissionDenied
        form = ReasonForm(request.POST or None)
        if request.method == "POST" and form.is_valid():
            RevokeRoleAssignment()(assignment, form.cleaned_data["reason"], request.user)  # type: ignore[arg-type]
            messages.success(request, _("Assignment ended."))
            return HttpResponseRedirect(reverse("admin:security_user_change", args=[user_id]))
        return self._render_form(request, assignment.user, form, _("End assignment"), assignment=assignment)

    def _render_form(
        self, request: HttpRequest, user: User, form: forms.Form, title: Any, **extra: Any
    ) -> HttpResponse:
        context = {
            **self.admin_site.each_context(request),
            "title": title,
            "subtitle": user.display_name(),
            "form": form,
            "opts": self.model._meta,
            "original": user,
            "back_url": reverse("admin:security_user_change", args=[user.pk]),
            **extra,
        }
        return render(request, "security/admin/action_form.html", context)


def _aware(value: datetime | None) -> datetime | None:
    if value is None or timezone.is_aware(value):
        return value
    return timezone.make_aware(value)


def _send_password_reset_link(request: HttpRequest, user: User) -> None:
    from allauth.account.forms import ResetPasswordForm

    form = ResetPasswordForm(data={"email": user.email})
    if form.is_valid():
        form.save(request)


# -- roles ---------------------------------------------------------------------------------------
_NAME_PATTERN = re.compile(r"^[a-z][a-z0-9_]*$")


def _permission_fields() -> dict[str, forms.Field]:
    """One checkbox list per resource (original ``RoleForm::permissionFields``)."""
    return {
        f"permissions__{resource}": forms.MultipleChoiceField(
            label=Permission.resource_label(resource),
            required=False,
            choices=[(permission.value, permission.label) for permission in permissions],
            widget=UnfoldAdminCheckboxSelectMultipleWidget,
        )
        for resource, permissions in Permission.grouped_by_resource().items()
    }


class _RoleAdminFormBase(forms.ModelForm):  # type: ignore[type-arg]
    class Meta:
        model = Role
        fields = ("name", "display_name", "description")
        labels = {"name": _("Internal name"), "display_name": _("Display name"), "description": _("Description")}
        help_texts = {"name": _("Lowercase letters, digits and underscores, e.g. registrar.")}

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        role: Role = self.instance
        locked = bool(role.pk and (role.is_system or role.is_persona()))
        self.fields["name"].disabled = locked
        self.fields["name"].max_length = 100  # type: ignore[attr-defined]
        held = set(role.permission_names()) if role.pk else set()
        for resource, permissions in Permission.grouped_by_resource().items():
            field = self.fields[f"permissions__{resource}"]
            field.initial = [permission.value for permission in permissions if permission.value in held]
            field.disabled = bool(role.pk and role.is_system)

    def clean_name(self) -> str:
        name = str(self.cleaned_data["name"])
        if not _NAME_PATTERN.match(name):
            raise ValidationError(_("Lowercase letters, digits and underscores, e.g. registrar."))
        if Role.objects.filter(name=name, guard_name=GUARD_NAME).exclude(pk=self.instance.pk).exists():
            raise ValidationError(_("The name has already been taken."))
        return name

    def permission_names(self) -> list[str]:
        names: list[str] = []
        for resource in Permission.grouped_by_resource():
            names.extend(self.cleaned_data.get(f"permissions__{resource}") or [])
        return names


RoleAdminForm = type("RoleAdminForm", (_RoleAdminFormBase,), _permission_fields())


@admin.register(Role)
class RoleAdmin(CatalogAdmin):
    permissions: ClassVar[dict[str, str]] = {
        "view": Permission.ROLES_VIEW,
        "add": Permission.ROLES_MANAGE,
        "change": Permission.ROLES_MANAGE,
        "delete": Permission.ROLES_MANAGE,
    }
    navigation_group = NavigationGroup.ACCESS
    navigation_icon = "key"
    navigation_label = pgettext_lazy("admin", "Roles")
    navigation_order = 20
    form = RoleAdminForm
    list_display = (
        "display_name_column",
        "name",
        "persona_column",
        "is_system",
        "permissions_count",
        "active_assignments_count",
    )
    search_fields = ("name",)
    ordering = ("name",)

    def get_fieldsets(self, request: HttpRequest, obj: Any = None) -> Any:
        permission_fields = [f"permissions__{resource}" for resource in Permission.grouped_by_resource()]
        description = _("System roles always have every permission.") if obj is not None and obj.is_system else None
        return (
            (_("General"), {"fields": ("name", "display_name", "description")}),
            (_("Permissions"), {"fields": permission_fields, "description": description}),
        )

    def get_queryset(self, request: HttpRequest) -> Any:
        now = timezone.now()
        active = (Q(assignments__starts_at__isnull=True) | Q(assignments__starts_at__lte=now)) & (
            Q(assignments__ends_at__isnull=True) | Q(assignments__ends_at__gt=now)
        )
        return (
            super()
            .get_queryset(request)
            .annotate(
                permission_total=Count("permissions", distinct=True),
                active_assignment_total=Count(
                    "assignments", filter=active & Q(assignments__isnull=False), distinct=True
                ),
            )
        )

    def has_delete_permission(self, request: HttpRequest, obj: Any = None) -> bool:
        if obj is None:
            return super().has_delete_permission(request, obj)
        return bool(request.user.has_perm("delete", obj))

    @display(description=_("Display name"))
    def display_name_column(self, obj: Role) -> str:
        return obj.display_label

    @display(description=_("Persona"))
    def persona_column(self, obj: Role) -> str:
        return Persona(obj.persona).label if obj.persona else "-"

    @display(description=_("Permissions"), ordering="permission_total")
    def permissions_count(self, obj: Role) -> int:
        return int(getattr(obj, "permission_total", 0))

    @display(description=_("Active assignments"), ordering="active_assignment_total")
    def active_assignments_count(self, obj: Role) -> int:
        return int(getattr(obj, "active_assignment_total", 0))

    def save_model(self, request: HttpRequest, obj: Role, form: Any, change: bool) -> None:
        if change and (obj.is_system or obj.is_persona()):
            obj.name = Role.objects.get(pk=obj.pk).name
        obj.guard_name = GUARD_NAME
        obj.save()

    def save_related(self, request: HttpRequest, form: Any, formsets: Any, change: bool) -> None:
        super().save_related(request, form, formsets, change)
        role: Role = form.instance
        if not role.is_system:
            UpdateRolePermissions()(role, form.permission_names(), request.user)  # type: ignore[arg-type]


# Settings pages for the security and authentication groups (registered on import).
from ninefruits.security import settings_pages  # noqa: E402, F401
