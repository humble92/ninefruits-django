"""Certificate kinds (original Filament ``CertificateTypeResource`` with
``TemplatesRelationManager``; legacy FCERT with one PDFlib script per kind and language): the
wording per language is a template the institution edits. Anyone with ``reference_data.view``
looks; ``certificates.manage`` changes."""

from __future__ import annotations

from typing import Any, ClassVar

from django import forms
from django.contrib import admin
from django.db.models import Count
from django.http import HttpRequest
from django.utils.translation import gettext, pgettext_lazy
from django.utils.translation import gettext_lazy as _
from unfold.admin import StackedInline
from unfold.decorators import display
from unfold.widgets import UnfoldAdminSelectWidget, UnfoldAdminTextareaWidget

from ninefruits.adminpanel.mixins import CatalogPermissionMixin
from ninefruits.adminpanel.navigation import NavigationGroup
from ninefruits.certificate.enums import CertificateAudience
from ninefruits.certificate.models import CertificateTemplate, CertificateType
from ninefruits.certificate.services.renderer import CertificateRenderer
from ninefruits.institution.admin_support import ReferenceAdmin
from ninefruits.security.enums import Permission

from .common import locale_choices


class CertificateTypeForm(forms.ModelForm):  # type: ignore[type-arg]
    code = forms.RegexField(
        label=pgettext_lazy("reference", "Code"),
        regex=r"^[A-Za-z0-9_-]+$",
        max_length=32,
        help_text=_("Used in serial numbers, e.g. ENR, GRD, TRN."),
    )

    class Meta:
        model = CertificateType
        fields = ("code", "audience", "name", "has_grades", "has_photo", "is_active", "sort_order")


class CertificateTemplateForm(forms.ModelForm):  # type: ignore[type-arg]
    locale = forms.ChoiceField(label=pgettext_lazy("common", "Language"), widget=UnfoldAdminSelectWidget)

    class Meta:
        model = CertificateTemplate
        fields = ("locale", "title", "body", "footer", "signer")
        widgets = {
            "body": UnfoldAdminTextareaWidget(attrs={"rows": 6}),
            "footer": UnfoldAdminTextareaWidget(attrs={"rows": 2}),
        }

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        choices = locale_choices()
        current = self.instance.locale if self.instance.pk else None
        if current and current not in dict(choices):
            choices.append((current, current))
        self.fields["locale"].choices = [("", "---------"), *choices]  # type: ignore[attr-defined]
        self.fields["body"].help_text = gettext(
            "Paragraphs separated by a blank line. Placeholders: %(placeholders)s"
        ) % {"placeholders": CertificateRenderer.placeholder_help()}
        self.fields["footer"].max_length = 1000  # type: ignore[attr-defined]


class CertificateTemplateInline(CatalogPermissionMixin, StackedInline):
    """The wording of a kind per language. Placeholders in braces are filled at issue time."""

    model = CertificateTemplate
    fk_name = "certificate_type"
    form = CertificateTemplateForm
    extra = 0
    verbose_name = _("Templates")
    verbose_name_plural = _("Templates")
    ordering = ("locale",)
    permissions: ClassVar[dict[str, str]] = {
        "view": Permission.REFERENCE_DATA_VIEW,
        "add": Permission.CERTIFICATES_MANAGE,
        "change": Permission.CERTIFICATES_MANAGE,
        "delete": Permission.CERTIFICATES_MANAGE,
    }

    def has_add_permission(self, request: HttpRequest, obj: Any = None) -> bool:
        return self._allowed(request, "add")


@admin.register(CertificateType)
class CertificateTypeAdmin(ReferenceAdmin):
    manage_permission = Permission.CERTIFICATES_MANAGE
    navigation_group = NavigationGroup.CERTIFICATES
    navigation_icon = "verified"
    navigation_order = 20
    form = CertificateTypeForm
    list_display = ("code", "name_column", "audience_label", "templates_count", "has_grades", "is_active")
    search_fields = ("code",)
    ordering = ("sort_order", "id")
    inlines = (CertificateTemplateInline,)

    def get_queryset(self, request: HttpRequest) -> Any:
        return super().get_queryset(request).annotate(template_total=Count("templates"))

    @display(description=pgettext_lazy("reference", "Name"))
    def name_column(self, obj: CertificateType) -> str:
        return str(obj.name or "")

    @display(description=pgettext_lazy("certificate", "For"))
    def audience_label(self, obj: CertificateType) -> str:
        return str(CertificateAudience(obj.audience).label)

    @display(description=_("Templates"), ordering="template_total")
    def templates_count(self, obj: CertificateType) -> int:
        return int(getattr(obj, "template_total", 0))
