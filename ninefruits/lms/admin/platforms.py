"""LMS platforms (original Filament ``LmsPlatformResource``; docs/lms-integration-guide.md).
Credentials are written, never shown: the field is always empty and an empty field on edit keeps
the stored values."""

from __future__ import annotations

from typing import Any, ClassVar

from django import forms
from django.contrib import admin
from django.db.models import Count
from django.http import HttpRequest
from django.utils.translation import gettext, pgettext_lazy
from django.utils.translation import gettext_lazy as _
from unfold.decorators import display
from unfold.widgets import UnfoldAdminSelectWidget, UnfoldAdminTextareaWidget

from ninefruits.adminpanel.mixins import CatalogAdmin
from ninefruits.adminpanel.navigation import NavigationGroup
from ninefruits.lms.actions import SavePlatform
from ninefruits.lms.connectors import connectors
from ninefruits.lms.enums import LmsDriver
from ninefruits.lms.models import LmsPlatform
from ninefruits.security.enums import Permission

CREDENTIALS_MAX = 4000


def driver_choices() -> list[tuple[str, str]]:
    registry = connectors()
    return [
        (value, str(label) if registry.is_implemented(value) else f"{label} ({gettext('not implemented yet')})")
        for value, label in LmsDriver.choices
    ]


def parse_credentials(text: str) -> dict[str, str]:
    """``key=value`` per line (blank lines and lines starting with ``#`` are ignored)."""
    values: dict[str, str] = {}
    for number, raw in enumerate(text.splitlines(), start=1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        key, sep, value = line.partition("=")
        if not sep or not key.strip():
            raise forms.ValidationError(
                gettext("Line %(number)s: write key=value.") % {"number": number}, code="invalid_credentials"
            )
        values[key.strip()] = value.strip()
    return values


class LmsPlatformForm(forms.ModelForm):  # type: ignore[type-arg]
    code = forms.RegexField(label=pgettext_lazy("reference", "Code"), regex=r"^[A-Za-z0-9_-]+$", max_length=32)
    driver = forms.ChoiceField(
        label=_("Driver"),
        widget=UnfoldAdminSelectWidget,
        help_text=_(
            'The connector that talks to the platform. "null" records what would be sent without calling '
            "anything; use it to prepare and test."
        ),
    )
    base_url = forms.URLField(label=_("Base URL"), max_length=255, required=False, assume_scheme="https")
    credentials_text = forms.CharField(
        label=_("Credentials"),
        required=False,
        max_length=CREDENTIALS_MAX,
        widget=UnfoldAdminTextareaWidget(attrs={"rows": 3, "autocomplete": "off", "spellcheck": "false"}),
        help_text=_(
            "Tokens and secrets the driver needs (see docs/lms-integration-guide.md). Stored encrypted; leave "
            "empty on edit to keep the stored ones."
        )
        + " "
        + _("One key=value per line, e.g. token=..."),
    )

    class Meta:
        model = LmsPlatform
        fields = ("code", "name", "driver", "base_url", "is_active", "should_sync_enrollments", "should_pull_grades")
        help_texts: ClassVar[dict[str, Any]] = {
            "is_active": _(
                "Active platforms receive published sections and roster changes as they happen, and the nightly "
                "reconcile."
            ),
            "should_pull_grades": _(
                "Lets instructors load the platform's final scores into the grade entry screen as a draft."
            ),
        }

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.fields["driver"].choices = driver_choices()  # type: ignore[attr-defined]
        if not self.instance.pk:
            self.fields["driver"].initial = LmsDriver.NULL
        self.fields["credentials_text"].initial = ""

    def clean_code(self) -> str:
        code = str(self.cleaned_data["code"])
        clash = LmsPlatform.objects.filter(code=code).exclude(pk=self.instance.pk)
        if clash.exists():
            raise forms.ValidationError(gettext("This code is already used."))
        return code

    def clean_credentials_text(self) -> dict[str, str]:
        return parse_credentials(self.cleaned_data.get("credentials_text") or "")


@admin.register(LmsPlatform)
class LmsPlatformAdmin(CatalogAdmin):
    permissions: ClassVar[dict[str, str]] = {
        "view": Permission.LMS_MANAGE,
        "add": Permission.LMS_MANAGE,
        "change": Permission.LMS_MANAGE,
    }
    navigation_group = NavigationGroup.LMS
    navigation_icon = "dns"
    navigation_order = 10
    form = LmsPlatformForm
    fieldsets = (
        (None, {"fields": ("code", "driver", "name", "base_url", "credentials_text")}),
        (None, {"fields": ("is_active", "should_sync_enrollments", "should_pull_grades")}),
    )
    list_display = (
        "code",
        "name_column",
        "driver_column",
        "base_url_column",
        "links_count",
        "is_active",
        "should_sync_enrollments",
        "should_pull_grades",
    )
    list_display_links = ("code",)
    search_fields = ("code",)
    ordering = ("code",)

    def get_queryset(self, request: HttpRequest) -> Any:
        return super().get_queryset(request).annotate(link_total=Count("course_links"))

    @display(description=pgettext_lazy("reference", "Name"))
    def name_column(self, obj: LmsPlatform) -> str:
        return str(obj.name or "")

    @display(description=_("Driver"))
    def driver_column(self, obj: LmsPlatform) -> str:
        return dict(driver_choices()).get(obj.driver, obj.driver)

    @display(description=_("Base URL"))
    def base_url_column(self, obj: LmsPlatform) -> str:
        url = obj.base_url or "-"
        return url if len(url) <= 40 else url[:39] + "…"

    @display(description=_("Course links"), ordering="link_total")
    def links_count(self, obj: LmsPlatform) -> int:
        return int(getattr(obj, "link_total", 0))

    def save_model(self, request: HttpRequest, obj: LmsPlatform, form: Any, change: bool) -> None:
        SavePlatform()(obj, request.user, form.cleaned_data.get("credentials_text") or None)
