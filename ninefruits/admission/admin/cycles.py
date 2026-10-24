"""Admission cycles in the admin panel (original Filament ``AdmissionCycleResource``): when
applications are taken, which programs, which documents. Releasing a cycle's decisions is a row
action on the list and a button on the cycle."""

from __future__ import annotations

from typing import Any, ClassVar

from django import forms
from django.contrib import admin, messages
from django.core.exceptions import PermissionDenied
from django.core.validators import MinValueValidator
from django.db.models import Count
from django.http import HttpRequest, HttpResponse, HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from django.utils.translation import ngettext, pgettext_lazy
from unfold.admin import TabularInline
from unfold.decorators import action, display
from unfold.forms import BaseDialogForm

from ninefruits.adminpanel.mixins import CatalogPermissionMixin
from ninefruits.adminpanel.navigation import NavigationGroup
from ninefruits.admission.actions import ReleaseDecisions
from ninefruits.admission.enums import ApplicationStatus
from ninefruits.admission.models import (
    DOCUMENT_TYPE_LOOKUP,
    AdmissionCycle,
    AdmissionCycleDocumentType,
    AdmissionCycleProgram,
    Application,
)
from ninefruits.i18n.forms import TranslatableFormField
from ninefruits.institution.admin_support import ReferenceAdmin
from ninefruits.institution.models import LookupValue
from ninefruits.organization.models import Program
from ninefruits.security.enums import Permission

RELEASE_HELP = _("Applicants see their decision and get an email. A released decision can no longer be changed.")


class ReleaseDecisionsForm(BaseDialogForm):
    """Confirmation only."""


class AdmissionCycleForm(forms.ModelForm):  # type: ignore[type-arg]
    description = TranslatableFormField(
        label=pgettext_lazy("admissions", "Description"), required=False, textarea=True, max_length=2000
    )

    class Meta:
        model = AdmissionCycle
        fields = (
            "code",
            "is_published",
            "name",
            "description",
            "opens_at",
            "closes_at",
            "should_release_decisions_immediately",
            "offer_response_days",
        )

    def clean_code(self) -> str:
        code = str(self.cleaned_data["code"]).strip()
        if not all(ch.isalnum() or ch in "-_" for ch in code):
            raise forms.ValidationError(_("Use only letters, numbers, dashes and underscores."))
        return code


def _with_blank(choices: list[tuple[Any, Any]]) -> list[tuple[Any, Any]]:
    return [("", "---------"), *choices]


class CycleProgramForm(forms.ModelForm):  # type: ignore[type-arg]
    class Meta:
        model = AdmissionCycleProgram
        fields = ("program", "capacity")

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        current = Program.objects.effective_on()
        if self.instance.pk:
            current = current | Program.objects.filter(pk=self.instance.program_id)
        self.fields["program"].queryset = current.distinct()  # type: ignore[attr-defined]
        self.fields["capacity"].validators.append(MinValueValidator(0))


class CycleProgramInline(CatalogPermissionMixin, TabularInline):  # type: ignore[misc]
    model = AdmissionCycleProgram
    form = CycleProgramForm
    extra = 0
    tab = True
    fields = ("program", "capacity", "applications_count")
    readonly_fields = ("applications_count",)
    verbose_name = _("program offered")
    verbose_name_plural = _("Programs offered")
    permissions: ClassVar[dict[str, str]] = {
        "view": Permission.ADMISSION_CYCLES_MANAGE,
        "add": Permission.ADMISSION_CYCLES_MANAGE,
        "change": Permission.ADMISSION_CYCLES_MANAGE,
        "delete": Permission.ADMISSION_CYCLES_MANAGE,
    }

    def has_view_permission(self, request: HttpRequest, obj: Any = None) -> bool:
        return bool(request.user.has_perm("view_any", AdmissionCycle))

    def has_add_permission(self, request: HttpRequest, obj: Any = None) -> bool:
        return self._allowed(request, "add")

    @display(description=_("applications"))
    def applications_count(self, obj: AdmissionCycleProgram) -> int:
        """Shown to staff when deciding; capacity is not enforced."""
        if obj.pk is None:
            return 0
        return (
            Application.objects.filter(admission_cycle_id=obj.admission_cycle_id, program_id=obj.program_id)
            .exclude(status=ApplicationStatus.DRAFT)
            .count()
        )


class CycleDocumentTypeForm(forms.ModelForm):  # type: ignore[type-arg]
    class Meta:
        model = AdmissionCycleDocumentType
        fields = ("document_type", "is_required")

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.fields["document_type"].queryset = LookupValue.objects.of_type(DOCUMENT_TYPE_LOOKUP).filter(  # type: ignore[attr-defined]
            is_active=True
        )


class CycleDocumentTypeInline(CycleProgramInline):
    model = AdmissionCycleDocumentType
    form = CycleDocumentTypeForm
    fields = ("document_type", "is_required")
    readonly_fields = ()
    verbose_name = _("document")
    verbose_name_plural = _("Documents")


@admin.register(AdmissionCycle)
class AdmissionCycleAdmin(ReferenceAdmin):
    permissions: ClassVar[dict[str, str]] = {
        "view": Permission.ADMISSION_CYCLES_MANAGE,
        "add": Permission.ADMISSION_CYCLES_MANAGE,
        "change": Permission.ADMISSION_CYCLES_MANAGE,
        "delete": Permission.ADMISSION_CYCLES_MANAGE,
    }
    navigation_group = NavigationGroup.ADMISSIONS
    navigation_icon = "calendar_month"
    navigation_order = 10
    form = AdmissionCycleForm
    inlines = (CycleProgramInline, CycleDocumentTypeInline)
    list_display = ("code", "name", "opens_at", "closes_display", "is_published", "applications_total")
    search_fields = ("code",)
    ordering = ("-opens_at",)
    actions_row = ("release_decisions",)
    actions_detail = ("release_cycle_decisions",)
    fieldsets = (
        (
            _("Cycle"),
            {
                "fields": (
                    ("code", "is_published"),
                    "name",
                    "description",
                    ("opens_at", "closes_at"),
                    ("should_release_decisions_immediately", "offer_response_days"),
                )
            },
        ),
    )

    def has_view_permission(self, request: HttpRequest, obj: Any = None) -> bool:
        return bool(request.user.has_perm("view_any", AdmissionCycle))

    def get_queryset(self, request: HttpRequest) -> Any:
        return super().get_queryset(request).annotate(application_total=Count("applications"))

    @display(description=pgettext_lazy("admissions", "Closes"), ordering="closes_at")
    def closes_display(self, obj: AdmissionCycle) -> Any:
        if obj.closes_at is None:
            return _("Rolling (no deadline)")
        from django.utils import formats, timezone

        return formats.date_format(timezone.localtime(obj.closes_at), "DATETIME_FORMAT")

    @display(description=_("applications"), ordering="application_total")
    def applications_total(self, obj: AdmissionCycle) -> int:
        return int(getattr(obj, "application_total", 0) or 0)

    # -- release decisions (original AdmissionCycleResource::releaseAction) ----------------------
    def has_release_permission(self, request: HttpRequest, object_id: Any = None) -> bool:
        return bool(request.user.has_perm("view_any", Application))

    def _release(self, request: HttpRequest, object_id: Any) -> HttpResponse:
        if not self.has_release_permission(request):
            raise PermissionDenied
        cycle = get_object_or_404(AdmissionCycle, pk=object_id)
        applications = (
            Application.objects.visible_to(request.user)
            .filter(
                admission_cycle=cycle,
                status__in=[ApplicationStatus.ADMITTED, ApplicationStatus.REJECTED],
                decision_released_at__isnull=True,
            )
            .select_related("admission_cycle", "person", "program")
        )
        count = ReleaseDecisions().handle(applications, request.user)
        messages.success(request, released_message(count))
        return HttpResponseRedirect(
            request.headers.get("Referer") or reverse("admin:admission_admissioncycle_changelist")
        )

    @action(
        description=_("Release decisions"),
        url_path="release-decisions",
        permissions=["release"],
        icon="campaign",
        dialog={"title": _("Release decisions"), "description": RELEASE_HELP, "form_class": ReleaseDecisionsForm},
    )
    def release_decisions(self, request: HttpRequest, form: Any, object_id: Any) -> HttpResponse:
        return self._release(request, object_id)

    @action(
        description=_("Release decisions"),
        url_path="release-cycle-decisions",
        permissions=["release"],
        icon="campaign",
        dialog={"title": _("Release decisions"), "description": RELEASE_HELP, "form_class": ReleaseDecisionsForm},
    )
    def release_cycle_decisions(self, request: HttpRequest, form: Any, object_id: Any) -> HttpResponse:
        return self._release(request, object_id)


def released_message(count: int) -> str:
    if count == 0:
        return str(_("No decisions to release."))
    return ngettext("One decision released.", "%(count)s decisions released.", count) % {"count": count}
