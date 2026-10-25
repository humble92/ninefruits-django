"""The issue ledger (original Filament ``CertificateIssueResource``; legacy SRCERT had no issuer,
no status and hard deletes). Every issue stays; revocation keeps the row and the file and makes
the verification page say so. Rows of student records the user can see; nothing is created,
edited or deleted here (issues come from the student record's "Issue certificate")."""

from __future__ import annotations

from typing import Any

from django.contrib import admin
from django.contrib.admin.options import ActionLocation
from django.core.exceptions import PermissionDenied
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404
from django.urls import reverse
from django.utils.html import format_html
from django.utils.text import Truncator
from django.utils.translation import gettext, pgettext_lazy
from django.utils.translation import gettext_lazy as _
from unfold.decorators import action, display

from ninefruits.adminpanel.mixins import CatalogAdmin
from ninefruits.adminpanel.navigation import NavigationGroup
from ninefruits.certificate.actions import IssueCertificate, can_issue
from ninefruits.certificate.enums import CertificateIssueStatus
from ninefruits.certificate.models import CertificateIssue
from ninefruits.person.models import Person
from ninefruits.registration.admin.common import ChoiceFilter, run_form

from .common import ConfirmForm, RevokeForm

STATUS_COLORS = {
    CertificateIssueStatus.ISSUED.label: "success",
    CertificateIssueStatus.REVOKED.label: "danger",
}


class IssueStatusFilter(ChoiceFilter):
    title = pgettext_lazy("registration", "Status")
    parameter_name = "status"
    choices_class = CertificateIssueStatus
    default = "all"


class CertificateTypeFilter(admin.SimpleListFilter):
    title = pgettext_lazy("certificate", "Kind")
    parameter_name = "type"

    def lookups(self, request: HttpRequest, model_admin: Any) -> list[tuple[Any, Any]]:
        from ninefruits.certificate.models import CertificateType

        return [(kind.pk, str(kind.name)) for kind in CertificateType.objects.order_by("sort_order", "id")]

    def queryset(self, request: HttpRequest, queryset: Any) -> Any:
        value = self.value()
        return queryset.filter(certificate_type_id=value) if value and str(value).isdigit() else queryset


@admin.register(CertificateIssue)
class CertificateIssueAdmin(CatalogAdmin):
    navigation_group = NavigationGroup.CERTIFICATES
    navigation_icon = "assignment"
    navigation_order = 10
    list_display = (
        "issued_at",
        "serial_number",
        "kind",
        "student_number",
        "name",
        "purpose_short",
        "copies",
        "status_badge",
        "issued_by_email",
        "links",
    )
    list_filter = (CertificateTypeFilter, IssueStatusFilter)
    list_select_related = ("student_record__person", "certificate_type", "issued_by")
    search_fields = ("serial_number",)
    ordering = ("-issued_at", "-id")
    list_per_page = 50
    actions_row = ("rerender_row", "revoke_row")
    fields = (
        "serial_number",
        "kind",
        "student_number",
        "name",
        "purpose",
        "copies",
        "status_badge",
        "issued_at",
        "issued_by_email",
        "pdf_checksum",
        "revoked_at",
        "revocation_reason",
        "links",
    )
    readonly_fields = fields

    # -- access (original CertificateIssuePolicy) -------------------------------------------------
    def has_view_permission(self, request: HttpRequest, obj: Any = None) -> bool:
        return self.policy_allows(request, "view_any", CertificateIssue)

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
            queryset.filter(serial_number__icontains=term)
            | queryset.filter(student_record__student_number__icontains=term)
            | queryset.filter(student_record__person__in=people),
            False,
        )

    # -- columns ---------------------------------------------------------------------------------
    @display(description=pgettext_lazy("certificate", "Kind"))
    def kind(self, obj: CertificateIssue) -> str:
        return f"{obj.certificate_type.name} ({obj.locale})"

    @display(description=_("Student number"), ordering="student_record__student_number")
    def student_number(self, obj: CertificateIssue) -> str:
        return str(obj.student_record.student_number)

    @display(description=pgettext_lazy("people", "Name"))
    def name(self, obj: CertificateIssue) -> str:
        return str(obj.student_record.person.display_name())

    @display(description=_("Purpose"))
    def purpose_short(self, obj: CertificateIssue) -> str:
        return Truncator(obj.purpose).chars(30) if obj.purpose else "-"

    @display(description=pgettext_lazy("registration", "Status"), label=STATUS_COLORS)
    def status_badge(self, obj: CertificateIssue) -> str:
        return str(CertificateIssueStatus(obj.status).label)

    @display(description=_("Issued by"))
    def issued_by_email(self, obj: CertificateIssue) -> str:
        return str(obj.issued_by.email) if obj.issued_by else "-"

    @display(description="")
    def links(self, obj: CertificateIssue) -> str:
        """``PDF`` and ``Verification page`` (original row actions opening a new tab)."""
        return format_html(
            '<a class="underline" href="{}" target="_blank" rel="noopener">{}</a> · '
            '<a class="underline" href="{}" target="_blank" rel="noopener">{}</a>',
            reverse("certificate:download", args=[obj.pk]),
            gettext("PDF"),
            reverse("certificate:verify", args=[obj.verification_code]),
            gettext("Verification page"),
        )

    # -- row actions -----------------------------------------------------------------------------
    def _issue(self, request: HttpRequest, object_id: Any) -> CertificateIssue:
        issue: CertificateIssue = get_object_or_404(
            self.get_queryset(request).select_related("certificate_type", "student_record"), pk=object_id
        )
        return issue

    def _changelist_url(self) -> str:
        return reverse("admin:certificate_certificateissue_changelist")

    def _subtitle(self, issue: CertificateIssue) -> str:
        return f"{issue.serial_number} · {issue.certificate_type.name} ({issue.locale}) · {issue.student_record}"

    def has_issue_permission(self, request: HttpRequest, object_id: Any = None) -> bool:
        return can_issue(request.user)

    @action(description=_("Render again"), url_path="rerender", permissions=["issue"], icon="refresh")
    def rerender_row(self, request: HttpRequest, object_id: Any) -> HttpResponse:
        issue = self._issue(request, object_id)
        if issue.is_revoked:
            raise PermissionDenied
        form = ConfirmForm(request.POST if request.method == "POST" else None)

        def perform(form: Any) -> str:
            from ninefruits.pdf import PdfRenderingError

            try:
                IssueCertificate().rerender(issue, request.user)
            except PdfRenderingError as error:
                from django.core.exceptions import ValidationError

                raise ValidationError(gettext("The PDF could not be created. Try again later.")) from error
            return gettext("Saved")

        return run_form(
            self,
            request,
            form,
            _("Render again"),
            self._changelist_url(),
            perform,
            subtitle=self._subtitle(issue),
            description=_(
                "Renders the PDF again from the current data and template. The serial number and verification "
                "code stay."
            ),
        )

    @action(description=pgettext_lazy("certificate", "Revoke"), url_path="revoke", permissions=["issue"], icon="block")
    def revoke_row(self, request: HttpRequest, object_id: Any) -> HttpResponse:
        issue = self._issue(request, object_id)
        form = RevokeForm(request.POST or None)

        def perform(form: Any) -> str:
            IssueCertificate().revoke(issue, request.user, form.cleaned_data["reason"])
            return str(CertificateIssueStatus.REVOKED.label)

        return run_form(
            self,
            request,
            form,
            pgettext_lazy("certificate", "Revoke"),
            self._changelist_url(),
            perform,
            subtitle=self._subtitle(issue),
        )
