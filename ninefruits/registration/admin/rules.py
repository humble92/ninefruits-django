"""Registration rules and credit limits (original Filament ``Resources/Registration/RuleSets``
with its rules relation manager, and ``CreditLimitPolicies``).

- Rule sets: one per term, prepared by copying another term's set or from the defaults; the set
  page lists its rules, each edited on its own page (enabled, block or warn, overrides allowed,
  the rule's parameters).
- Credit limits: term type, students, maximum credits, priority."""

from __future__ import annotations

from typing import Any

from django import forms
from django.contrib import admin
from django.contrib.admin.options import ActionLocation
from django.db.models import Count, Q
from django.http import HttpRequest, HttpResponse, HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.urls import reverse
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _
from django.utils.translation import pgettext_lazy
from unfold.admin import TabularInline
from unfold.decorators import action, display
from unfold.widgets import (
    UnfoldAdminCheckboxSelectMultipleWidget,
    UnfoldAdminIntegerFieldWidget,
    UnfoldAdminSelectWidget,
    UnfoldAdminTextInputWidget,
    UnfoldBooleanSwitchWidget,
)

from ninefruits.adminpanel.mixins import CatalogAdmin, CatalogPermissionMixin
from ninefruits.adminpanel.navigation import NavigationGroup
from ninefruits.institution.admin_support import render_action_form, show_errors
from ninefruits.institution.target_criteria_fields import TargetCriteriaForm, criteria_summary
from ninefruits.person.enums import StudentStatus
from ninefruits.registration.actions import PrepareRuleSet
from ninefruits.registration.enums import RuleCode, RuleSeverity
from ninefruits.registration.models import CreditLimitPolicy, RegistrationRule, RegistrationRuleSet
from ninefruits.security.enums import Permission
from ninefruits.term.models import Term, TermType

from .common import term_label

RULE_PERMISSIONS: dict[str, str] = {
    "view": Permission.REFERENCE_DATA_VIEW,
    "change": Permission.REGISTRATION_RULES_MANAGE,
}


# -- rule sets ------------------------------------------------------------------------------------
class PrepareRuleSetForm(forms.Form):
    term_id = forms.TypedChoiceField(label=_("term"), coerce=int, widget=UnfoldAdminSelectWidget)
    copy_from_id = forms.TypedChoiceField(
        label=pgettext_lazy("registration", "Copy from"),
        coerce=int,
        required=False,
        empty_value=None,
        widget=UnfoldAdminSelectWidget,
    )

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        terms = Term.objects.filter(status__in=["planned", "published"], registration_rule_set__isnull=True).order_by(
            "-start_date"
        )
        self.fields["term_id"].choices = [(t.pk, term_label(t)) for t in terms]  # type: ignore[attr-defined]
        sets = RegistrationRuleSet.objects.select_related("term").order_by("-term_id")
        self.fields["copy_from_id"].choices = [("", "-"), *((s.pk, term_label(s.term)) for s in sets)]  # type: ignore[attr-defined]
        latest = sets.first()
        self.fields["copy_from_id"].initial = latest.pk if latest else None


class RuleRowInline(CatalogPermissionMixin, TabularInline):  # type: ignore[misc]
    """The rules of a set, read only here; each is edited on its own page."""

    model = RegistrationRule
    permissions = RULE_PERMISSIONS
    extra = 0
    can_delete = False
    fields = ("rule_label", "is_enabled", "severity_label", "allows_override", "edit_link")
    readonly_fields = fields
    verbose_name = _("Rule")
    verbose_name_plural = _("Rules")

    def has_add_permission(self, request: HttpRequest, obj: Any = None) -> bool:
        return False

    def has_change_permission(self, request: HttpRequest, obj: Any = None) -> bool:
        return False

    def has_delete_permission(self, request: HttpRequest, obj: Any = None) -> bool:
        return False

    @display(description=_("Rule"))
    def rule_label(self, obj: RegistrationRule) -> Any:
        code = RuleCode(obj.rule_code)
        return format_html("{}<br><span class='text-xs text-base-500'>{}</span>", code.label, code.description)

    @display(description=_("When not met"))
    def severity_label(self, obj: RegistrationRule) -> str:
        return str(RuleSeverity(obj.severity).label)

    @display(description="")
    def edit_link(self, obj: RegistrationRule) -> Any:
        if obj.pk is None:
            return ""
        url = reverse("admin:registration_registrationrule_change", args=[obj.pk])
        return format_html('<a class="underline" href="{}">{}</a>', url, _("Edit"))


@admin.register(RegistrationRuleSet)
class RegistrationRuleSetAdmin(CatalogAdmin):
    permissions = RULE_PERMISSIONS
    navigation_group = NavigationGroup.REGISTRATION
    navigation_icon = "tune"
    navigation_order = 40
    fields = ("term_display", "copied_from_display", "note")
    readonly_fields = ("term_display", "copied_from_display")
    inlines = (RuleRowInline,)
    list_display = ("term_name", "term_code", "enabled_rules", "copied_from_name", "updated_at")
    list_select_related = ("term", "copied_from_rule_set__term")
    ordering = ("-term_id",)
    actions_list = ("prepare",)

    def get_queryset(self, request: HttpRequest) -> Any:
        return super().get_queryset(request).annotate(_enabled=Count("rules", filter=Q(rules__is_enabled=True)))

    def has_add_permission(self, request: HttpRequest, *args: Any) -> bool:
        return False

    def has_delete_permission(self, request: HttpRequest, obj: Any = None) -> bool:
        return False

    def get_actions(self, request: HttpRequest, action_location: Any = ActionLocation.CHANGE_LIST) -> dict[str, Any]:
        actions = super().get_actions(request, action_location)
        actions.pop("delete_selected", None)
        return actions

    def get_form(self, request: HttpRequest, obj: Any = None, change: bool = False, **kwargs: Any) -> Any:
        form = super().get_form(request, obj, change=change, **kwargs)
        if "note" in form.base_fields:
            form.base_fields["note"].max_length = 2000
        return form

    @display(description=_("term"), ordering="term__start_date")
    def term_name(self, obj: RegistrationRuleSet) -> str:
        return str(obj.term.name)

    @display(description=pgettext_lazy("reference", "Code"), label=True)
    def term_code(self, obj: RegistrationRuleSet) -> str:
        return obj.term.code

    @display(description=_("Rules on"))
    def enabled_rules(self, obj: RegistrationRuleSet) -> int:
        return int(getattr(obj, "_enabled", 0))

    @display(description=_("Copied from"))
    def copied_from_name(self, obj: RegistrationRuleSet) -> str:
        source = obj.copied_from_rule_set
        return str(source.term.name) if source is not None else "-"

    @display(description=_("term"))
    def term_display(self, obj: RegistrationRuleSet) -> str:
        return term_label(obj.term)

    @display(description=_("Copied from"))
    def copied_from_display(self, obj: RegistrationRuleSet) -> str:
        return self.copied_from_name(obj)

    def has_prepare_permission(self, request: HttpRequest) -> bool:
        return bool(request.user.has_perm("create", RegistrationRuleSet))

    @action(description=_("Prepare rules for a term"), url_path="prepare", permissions=["prepare"], icon="add")
    def prepare(self, request: HttpRequest) -> HttpResponse:
        from django.core.exceptions import ValidationError

        form = PrepareRuleSetForm(request.POST or None)
        back = reverse("admin:registration_registrationruleset_changelist")
        if request.method == "POST" and form.is_valid():
            term = get_object_or_404(Term, pk=form.cleaned_data["term_id"])
            source_id = form.cleaned_data.get("copy_from_id")
            source = RegistrationRuleSet.objects.filter(pk=source_id).first() if source_id else None
            try:
                rule_set = PrepareRuleSet().handle(term, source, request.user)
            except ValidationError as error:
                show_errors(request, error)
            else:
                return HttpResponseRedirect(
                    reverse("admin:registration_registrationruleset_change", args=[rule_set.pk])
                )
        return render_action_form(
            self,
            request,
            form,
            _("Prepare rules for a term"),
            back,
            description=_(
                "The rules are copied from the chosen term, or start from the defaults. "
                "Review them before registration opens."
            ),
        )


# -- one rule -------------------------------------------------------------------------------------
class RuleForm(forms.ModelForm):  # type: ignore[type-arg]
    """The common settings and the rule's own parameters (original ``RulesRelationManager``)."""

    statuses = forms.MultipleChoiceField(
        label=_("Student statuses that may register"),
        choices=StudentStatus.choices,
        required=False,
        widget=UnfoldAdminCheckboxSelectMultipleWidget,
    )
    allowed_overlap_minutes = forms.IntegerField(
        label=_("Allowed overlap (minutes)"),
        min_value=0,
        max_value=60,
        required=False,
        initial=0,
        widget=UnfoldAdminIntegerFieldWidget,
    )
    allowed = forms.BooleanField(label=_("Retakes allowed"), required=False, widget=UnfoldBooleanSwitchWidget)
    max_attempts = forms.IntegerField(
        label=_("Maximum attempts per course"),
        min_value=1,
        max_value=10,
        required=False,
        help_text=_("Including the first attempt. Empty means no limit."),
        widget=UnfoldAdminIntegerFieldWidget,
    )
    below_grade = forms.CharField(
        label=_("Only below grade"),
        max_length=4,
        required=False,
        help_text=_("Retake only when the earlier grade is below this grade (e.g. C+). Empty means any grade."),
        widget=UnfoldAdminTextInputWidget,
    )

    #: Parameter inputs per rule.
    PARAMETERS: dict[RuleCode, tuple[str, ...]] = {
        RuleCode.STUDENT_STATUS: ("statuses",),
        RuleCode.TIME_CONFLICT: ("allowed_overlap_minutes",),
        RuleCode.REPEAT_COURSE: ("allowed", "max_attempts", "below_grade"),
    }

    class Meta:
        model = RegistrationRule
        fields = ("is_enabled", "allows_override", "severity")
        widgets = {
            "is_enabled": UnfoldBooleanSwitchWidget,
            "allows_override": UnfoldBooleanSwitchWidget,
            "severity": UnfoldAdminSelectWidget,
        }

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        code = RuleCode(self.instance.rule_code)
        parameters = self.instance.parameters or {}
        for name in ("statuses", "allowed_overlap_minutes", "allowed", "max_attempts", "below_grade"):
            if name not in self.PARAMETERS.get(code, ()):
                del self.fields[name]
            elif name in parameters:
                self.initial[name] = parameters[name]
        if code == RuleCode.STUDENT_STATUS:
            self.fields["statuses"].required = True
        if code == RuleCode.REPEAT_COURSE:
            self.initial.setdefault("allowed", True)

    def clean_parameters(self) -> dict[str, Any]:
        """Keeps the known parameters with their types; empty optional values become null."""
        data = self.cleaned_data
        match RuleCode(self.instance.rule_code):
            case RuleCode.STUDENT_STATUS:
                return {"statuses": list(data.get("statuses") or [])}
            case RuleCode.TIME_CONFLICT:
                return {"allowed_overlap_minutes": int(data.get("allowed_overlap_minutes") or 0)}
            case RuleCode.REPEAT_COURSE:
                return {
                    "allowed": bool(data.get("allowed")),
                    "max_attempts": data.get("max_attempts") or None,
                    "below_grade": (data.get("below_grade") or "").strip() or None,
                }
        return {}

    def save(self, commit: bool = True) -> Any:
        self.instance.parameters = self.clean_parameters() or None
        return super().save(commit)


@admin.register(RegistrationRule)
class RegistrationRuleAdmin(CatalogAdmin):
    permissions = RULE_PERMISSIONS
    navigation_group = NavigationGroup.REGISTRATION
    navigation_hidden = True
    form = RuleForm
    readonly_fields = ("rule_display",)

    def get_fields(self, request: HttpRequest, obj: Any = None) -> Any:
        parameters = RuleForm.PARAMETERS.get(RuleCode(obj.rule_code), ()) if obj is not None else ()
        return ("rule_display", "is_enabled", "allows_override", "severity", *parameters)

    def has_add_permission(self, request: HttpRequest, *args: Any) -> bool:
        return False

    def has_delete_permission(self, request: HttpRequest, obj: Any = None) -> bool:
        return False

    @display(description=_("Rule"))
    def rule_display(self, obj: RegistrationRule) -> Any:
        code = RuleCode(obj.rule_code)
        return format_html(
            "<strong>{}</strong><br>{}<br>{}", code.label, code.description, term_label(obj.rule_set.term)
        )

    def _set_url(self, obj: RegistrationRule) -> str:
        return reverse("admin:registration_registrationruleset_change", args=[obj.rule_set_id])

    def response_change(self, request: HttpRequest, obj: RegistrationRule) -> HttpResponse:
        if "_continue" in request.POST:
            return super().response_change(request, obj)
        return HttpResponseRedirect(self._set_url(obj))

    def changelist_view(self, request: HttpRequest, extra_context: dict[str, Any] | None = None) -> Any:
        return HttpResponseRedirect(reverse("admin:registration_registrationruleset_changelist"))


# -- credit limits --------------------------------------------------------------------------------
class CreditLimitPolicyForm(TargetCriteriaForm):
    class Meta:
        model = CreditLimitPolicy
        fields = ("name", "term_type", "priority", "min_credits", "max_credits", "is_active")

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.fields["term_type"].queryset = TermType.objects.order_by("sort_order")  # type: ignore[attr-defined]
        self.fields["term_type"].empty_label = str(_("All term types"))  # type: ignore[attr-defined]
        for name in ("min_credits", "max_credits"):
            self.fields[name].min_value = 0  # type: ignore[attr-defined]
            self.fields[name].max_value = 99  # type: ignore[attr-defined]

    def clean(self) -> dict[str, Any]:
        cleaned = super().clean() or {}
        low, high = cleaned.get("min_credits"), cleaned.get("max_credits")
        if low is not None and high is not None and low > high:
            self.add_error(
                "min_credits",
                _("The %(attribute)s field must be less than or equal to %(value)s.")
                % {"attribute": _("Minimum credits"), "value": _("Maximum credits")},
            )
        for name in ("min_credits", "max_credits"):
            value = cleaned.get(name)
            if value is not None and not 0 <= value <= 99:
                self.add_error(
                    name,
                    _("The %(attribute)s field must be between %(min)s and %(max)s.")
                    % {"attribute": self.fields[name].label, "min": 0, "max": 99},
                )
        return cleaned


@admin.register(CreditLimitPolicy)
class CreditLimitPolicyAdmin(CatalogAdmin):
    permissions = {**RULE_PERMISSIONS, "add": Permission.REGISTRATION_RULES_MANAGE}
    navigation_group = NavigationGroup.REGISTRATION
    navigation_icon = "balance"
    navigation_order = 50
    form = CreditLimitPolicyForm
    list_display = ("name_display", "term_type_display", "applies_to", "max_credits", "priority", "is_active")
    list_select_related = ("term_type",)
    ordering = ("-priority", "id")
    fieldsets = (
        (None, {"fields": ("name", ("term_type", "priority"), ("min_credits", "max_credits"), "is_active")}),
        (
            pgettext_lazy("registration", "Students"),
            {
                "description": _("Leave empty for every student."),
                "fields": (
                    "eligibility__year_levels",
                    ("eligibility__admission_year_from", "eligibility__admission_year_to"),
                    "eligibility__program_ids",
                    "eligibility__org_unit_ids",
                ),
            },
        ),
    )

    def has_delete_permission(self, request: HttpRequest, obj: Any = None) -> bool:
        return False

    def get_actions(self, request: HttpRequest, action_location: Any = ActionLocation.CHANGE_LIST) -> dict[str, Any]:
        actions = super().get_actions(request, action_location)
        actions.pop("delete_selected", None)
        return actions

    @display(description=pgettext_lazy("reference", "Name"))
    def name_display(self, obj: CreditLimitPolicy) -> str:
        return str(obj.name or "")

    @display(description=_("term type"))
    def term_type_display(self, obj: CreditLimitPolicy) -> str:
        return str(obj.term_type.name) if obj.term_type_id else str(_("All term types"))

    @display(description=pgettext_lazy("registration", "Students"))
    def applies_to(self, obj: CreditLimitPolicy) -> str:
        return criteria_summary(obj.eligibility) or "-"
