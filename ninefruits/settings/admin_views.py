"""Admin pages that edit a settings group (original ``App\\Filament\\Admin\\Pages\\SettingsPage`` and
``Manage*Settings``), plus the "Settings" index listing the groups the user may manage.

Public API (used by the security work for the Security and Authentication pages)::

    from ninefruits.settings.admin_views import SettingsPage, Section, register_settings_page

    class SecuritySettingsForm(forms.Form):
        mfa_grace_period_days = forms.IntegerField(min_value=0, max_value=90, widget=UnfoldAdminIntegerFieldWidget)
        ...

    @register_settings_page
    class ManageSecuritySettings(SettingsPage):
        settings_class = SecuritySettings
        permission = Permission.SECURITY_SETTINGS_MANAGE
        slug = "security"                       # URL settings/security/, name "<site>:settings_security"
        title = _("Security")
        icon = "shield"                         # Material Symbols name (unfold)
        order = 10                              # position in the index and the menu
        form_class = SecuritySettingsForm
        sections = [Section(_("Two-factor authentication"), ["mfa_enforcement", ...],
                            description=_("Changes apply to every user immediately."))]

        def settings_data_from_form(self, cleaned_data):    # form state -> settings values
            return {...}

        def initial_from_settings(self, settings):           # optional: settings -> form initial
            return super().initial_from_settings(settings)

        def get_form_kwargs(self):                           # optional: extra form arguments
            return super().get_form_kwargs()

Saving validates the group (pydantic), writes it in a transaction and records the business audit
``settings.updated`` (log ``security``, properties ``group``, ``before``, ``after``) like the
original; the data audit trigger on ``settings`` records the rows. Access needs the admin panel
(``site.admin_view``) and ``request.user.has_perm(page.permission)``; otherwise 403.

URLs: ``get_settings_urls(site)`` returns the patterns for an ``AdminSite.get_urls()`` (the
adminpanel site includes them). ``sidebar_items()`` gives unfold sidebar entries.
Register pages in a module imported at startup (an app's ``admin`` module is autodiscovered).
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Any, ClassVar

from django import forms
from django.contrib import admin, messages
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.http import HttpRequest, HttpResponse, HttpResponseBase, HttpResponseRedirect
from django.template.response import TemplateResponse
from django.urls import URLPattern, path, reverse
from django.utils.functional import Promise
from django.utils.translation import gettext_lazy as _
from django.views import View

from ninefruits.settings.groups.base import SettingsGroup

_pages: dict[str, type[SettingsPage]] = {}


@dataclass(frozen=True)
class Section:
    """A titled group of form fields (original Filament ``Section``)."""

    title: str | Promise
    fields: Sequence[str]
    description: str | Promise = ""


@dataclass
class BoundSection:
    title: str | Promise
    description: str | Promise
    fields: list[forms.BoundField] = field(default_factory=list)


def register_settings_page(page: type[SettingsPage]) -> type[SettingsPage]:
    """Class decorator: adds the page to the settings index, the menu and the URLs."""
    for attribute in ("settings_class", "permission", "slug", "title", "form_class"):
        if not getattr(page, attribute, None):
            raise TypeError(f"{page.__name__}.{attribute} is required for a settings page.")
    _pages[page.slug] = page
    return page


def settings_pages() -> list[type[SettingsPage]]:
    return sorted(_pages.values(), key=lambda page: (page.order, str(page.title)))


def pages_for(request: HttpRequest) -> list[type[SettingsPage]]:
    return [page for page in settings_pages() if page.can_access(request)]


class SettingsPage(View):
    settings_class: ClassVar[type[SettingsGroup]]
    permission: ClassVar[str]
    slug: ClassVar[str]
    title: ClassVar[str | Promise]
    description: ClassVar[str | Promise] = ""
    icon: ClassVar[str] = "settings"
    order: ClassVar[int] = 100
    form_class: ClassVar[type[forms.Form]]
    sections: ClassVar[Sequence[Section]] = ()
    template_name: ClassVar[str] = "settings/page.html"
    audit_event: ClassVar[str] = "settings.updated"
    do_not_call_in_templates: ClassVar[bool] = True

    admin_site: admin.AdminSite = admin.site

    # -- access ----------------------------------------------------------------------------------
    @classmethod
    def can_access(cls, request: HttpRequest) -> bool:
        user = getattr(request, "user", None)
        return bool(user is not None and user.is_authenticated and user.has_perm(str(cls.permission)))

    @classmethod
    def url_name(cls) -> str:
        return f"settings_{cls.slug.replace('-', '_')}"

    @classmethod
    def url(cls, site: admin.AdminSite | None = None) -> str:
        return reverse(f"{(site or admin.site).name}:{cls.url_name()}")

    def dispatch(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponseBase:
        if not self.can_access(request):
            raise PermissionDenied
        return super().dispatch(request, *args, **kwargs)

    # -- settings <-> form -----------------------------------------------------------------------
    def load_settings(self) -> SettingsGroup:
        return self.settings_class.load()

    def initial_from_settings(self, settings: SettingsGroup) -> dict[str, Any]:
        """Form initial values; enums become their values (original ``formDataFromSettings``)."""
        return settings.model_dump(mode="json")

    def settings_data_from_form(self, cleaned_data: dict[str, Any]) -> dict[str, Any]:
        """Typed settings values from the form state (original ``settingsDataFromForm``).
        The default takes the form fields that are settings fields."""
        return {name: value for name, value in cleaned_data.items() if name in self.settings_class.model_fields}

    def get_form_kwargs(self) -> dict[str, Any]:
        return {}

    def get_form(self, data: Any = None, initial: dict[str, Any] | None = None) -> forms.Form:
        return self.form_class(data=data, initial=initial, **self.get_form_kwargs())

    # -- views -----------------------------------------------------------------------------------
    def get(self, request: HttpRequest) -> HttpResponse:
        form = self.get_form(initial=self.initial_from_settings(self.load_settings()))
        return self.render(request, form)

    def post(self, request: HttpRequest) -> HttpResponse:
        settings = self.load_settings()
        form = self.get_form(data=request.POST, initial=self.initial_from_settings(settings))
        if not form.is_valid():
            return self.render(request, form, status=422)
        try:
            self.save(settings, self.settings_data_from_form(form.cleaned_data))
        except ValueError as error:  # pydantic ValidationError is a ValueError
            form.add_error(None, str(error))
            return self.render(request, form, status=422)
        messages.success(request, _("Saved"))
        return HttpResponseRedirect(request.path)

    def save(self, settings: SettingsGroup, data: dict[str, Any]) -> SettingsGroup:
        from ninefruits.audit.logger import audit

        before = settings.model_dump(mode="json")
        updated = self.settings_class.model_validate({**before, **data})
        with transaction.atomic():
            updated.save()
            audit(
                self.audit_event,
                None,
                properties={
                    "group": self.settings_class.group,
                    "before": before,
                    "after": updated.model_dump(mode="json"),
                },
                log="security",
            )
        return updated

    def bound_sections(self, form: forms.Form) -> list[BoundSection]:
        sections = self.sections or [Section("", list(form.fields))]
        bound = [
            BoundSection(s.title, s.description, [form[name] for name in s.fields if name in form.fields])
            for s in sections
        ]
        listed = {name for s in sections for name in s.fields}
        rest = [form[name] for name in form.fields if name not in listed]
        if rest:
            bound.append(BoundSection("", "", rest))
        return bound

    def render(self, request: HttpRequest, form: forms.Form, status: int = 200) -> HttpResponse:
        context = {
            **self.admin_site.each_context(request),
            "title": self.title,
            "subtitle": self.description,
            "page": self,
            "group": self.settings_class.group,
            "form": form,
            "sections": self.bound_sections(form),
            "settings_pages": [(page, page.url(self.admin_site)) for page in pages_for(request)],
            "index_url": reverse(f"{self.admin_site.name}:settings_index"),
        }
        return TemplateResponse(request, self.template_name, context, status=status)


class SettingsIndexView(View):
    """ "Settings": the groups the user may manage."""

    admin_site: admin.AdminSite = admin.site
    template_name = "settings/index.html"

    def get(self, request: HttpRequest) -> HttpResponse:
        pages = pages_for(request)
        if not pages:
            raise PermissionDenied
        context = {
            **self.admin_site.each_context(request),
            "title": _("Settings"),
            "settings_pages": [(page, page.url(self.admin_site)) for page in pages],
        }
        return TemplateResponse(request, self.template_name, context)


def get_settings_urls(site: admin.AdminSite | None = None) -> list[URLPattern]:
    """URL patterns for ``AdminSite.get_urls()``: ``settings/`` and ``settings/<slug>/``."""
    site = site or admin.site
    patterns = [
        path(
            "settings/",
            site.admin_view(SettingsIndexView.as_view(admin_site=site)),
            name="settings_index",
        )
    ]
    for page in settings_pages():
        patterns.append(
            path(f"settings/{page.slug}/", site.admin_view(page.as_view(admin_site=site)), name=page.url_name())
        )
    return patterns


def sidebar_items(site_name: str = "admin") -> list[dict[str, Any]]:
    """Entries for an unfold ``SIDEBAR["navigation"]`` group (title, icon, link, permission)."""
    from django.urls import reverse_lazy

    items: list[dict[str, Any]] = []
    for page in settings_pages():
        items.append(
            {
                "title": page.title,
                "icon": page.icon,
                "link": reverse_lazy(f"{site_name}:{page.url_name()}"),
                "permission": page.can_access,
            }
        )
    return items
