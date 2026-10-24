"""Staff administration site (original ``AdminPanelProvider``).

There is no admin login form: unauthenticated users are sent to the shared allauth sign-in
(``/accounts/login/?next=...``), and two-factor enrollment happens in the portal (ADR 0001).
Opening the panel requires an active account with ``admin_panel.access``
(``ninefruits.security.authorization.can_access_admin``); a signed-in user without it gets 403,
as in the original.

Other apps add custom admin pages with :meth:`NinefruitsAdminSite.register_view`, or provide
URL patterns (``ninefruits.settings.admin_views.get_settings_urls``) that are mounted under
``/admin/`` and protected the same way.
"""

from __future__ import annotations

import importlib
import logging
from collections.abc import Callable
from dataclasses import dataclass
from functools import update_wrapper
from typing import Any

from django.conf import settings
from django.contrib.auth.views import redirect_to_login
from django.core.exceptions import PermissionDenied
from django.http import HttpRequest, HttpResponse, HttpResponseRedirect
from django.urls import URLPattern, URLResolver, path, reverse
from django.utils.csp import CSP
from django.utils.translation import pgettext_lazy
from django.views.decorators.csp import csp_override
from unfold.sites import UnfoldAdminSite

from .navigation import NavigationGroup, register_link

logger = logging.getLogger(__name__)

# unfold renders its components with the standard Alpine.js build, which evaluates
# expressions with ``new Function``. The admin therefore needs 'unsafe-eval' for scripts; the
# portal (Alpine CSP build) does not.
ADMIN_CSP: dict[str, Any] = {
    **settings.SECURE_CSP,
    "script-src": [CSP.SELF, CSP.NONCE, CSP.UNSAFE_EVAL],
    "style-src": [CSP.SELF, CSP.UNSAFE_INLINE],
    "img-src": [CSP.SELF, "data:"],
}

#: URL providers of other apps: (module, function). ``function(site)`` returns URL patterns
#: mounted under /admin/ whose views are wrapped in ``site.admin_view``.
EXTRA_URL_PROVIDERS: tuple[tuple[str, str], ...] = (("ninefruits.settings.admin_views", "get_settings_urls"),)


@dataclass(frozen=True)
class AdminViewEntry:
    route: str
    view: Callable[..., HttpResponse]
    name: str
    permission: str | None


class NinefruitsAdminSite(UnfoldAdminSite):  # type: ignore[misc]
    site_title = settings.APP_NAME
    site_header = settings.APP_NAME
    index_title = pgettext_lazy("admin", "Dashboard")
    site_url = "/portal/"
    enable_nav_sidebar = True
    # Dashboard: original Filament ``Dashboard`` page with the account widget.
    index_template = "adminpanel/dashboard.html"

    def __init__(self, name: str = "admin") -> None:
        super().__init__(name)
        self._custom_views: dict[str, AdminViewEntry] = {}

    # -- access ----------------------------------------------------------------------------
    def has_permission(self, request: HttpRequest) -> bool:
        from ninefruits.security.authorization import can_access_admin

        user = request.user
        return bool(user.is_authenticated and user.is_active and can_access_admin(user))

    def admin_view(self, view: Callable[..., Any], cacheable: bool = False) -> Callable[..., Any]:
        protected = super().admin_view(view, cacheable)

        def inner(request: HttpRequest, *args: Any, **kwargs: Any) -> Any:
            if request.path != reverse(f"{self.name}:logout", current_app=self.name):
                if not request.user.is_authenticated:
                    return redirect_to_login(request.get_full_path(), settings.LOGIN_URL)
                if not self.has_permission(request):
                    raise PermissionDenied
            return protected(request, *args, **kwargs)

        return csp_override(ADMIN_CSP)(update_wrapper(inner, protected))

    def login(self, request: HttpRequest, extra_context: dict[str, Any] | None = None) -> HttpResponse:
        """No admin login form: the shared allauth sign-in, back to the panel afterwards."""
        target = request.GET.get("next") or reverse(f"{self.name}:index", current_app=self.name)
        if request.user.is_authenticated:
            if not self.has_permission(request):
                raise PermissionDenied
            return HttpResponseRedirect(target)
        return redirect_to_login(target, settings.LOGIN_URL)

    def logout(self, request: HttpRequest, extra_context: dict[str, Any] | None = None) -> HttpResponse:
        """Signs out through allauth (signals, security events, redirect)."""
        from allauth.account.views import LogoutView

        response: HttpResponse = LogoutView.as_view()(request)
        return response

    # -- custom views ----------------------------------------------------------------------
    def register_view(
        self,
        route: str,
        view: Callable[..., HttpResponse],
        *,
        name: str,
        permission: str | None = None,
        navigation_group: NavigationGroup | None = None,
        label: Any = None,
        icon: str = "chevron_right",
        order: int = 100,
    ) -> None:
        """Adds a page under ``/admin/<route>`` named ``admin:<name>``.

        The page requires admin panel access and, when given, ``permission`` (403 otherwise).
        With ``navigation_group`` and ``label`` it also appears in the sidebar for users who
        hold ``permission``. Call from ``AppConfig.ready()``; URLs are built on first use.
        """
        self._custom_views[name] = AdminViewEntry(route, view, name, permission)
        if navigation_group is not None and label is not None:
            register_link(
                group=navigation_group,
                label=label,
                url_name=f"{self.name}:{name}",
                permission=permission,
                icon=icon,
                order=order,
            )

    def _permission_view(self, entry: AdminViewEntry) -> Callable[..., HttpResponse]:
        def view(request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
            if entry.permission and not request.user.has_perm(str(entry.permission)):
                raise PermissionDenied
            return entry.view(request, *args, **kwargs)

        return update_wrapper(view, entry.view)

    def provider_urls(self) -> list[URLPattern | URLResolver]:
        """URL patterns of other apps' providers; a provider receives the site and protects its
        views with ``site.admin_view``. A provider module that does not exist yet is skipped."""
        patterns: list[URLPattern | URLResolver] = []
        for module_name, function_name in EXTRA_URL_PROVIDERS:
            try:
                module = importlib.import_module(module_name)
            except ModuleNotFoundError as error:
                if error.name and module_name.startswith(error.name):
                    continue
                raise
            provider = getattr(module, function_name, None)
            if provider is not None:
                patterns.extend(provider(self))
        return patterns

    def extra_urls(self) -> list[URLPattern | URLResolver]:
        """Picked up by ``UnfoldAdminSite._get_extra_urls``."""
        custom = [
            path(entry.route, self.admin_view(self._permission_view(entry)), name=entry.name)
            for entry in self._custom_views.values()
        ]
        return [*custom, *self.provider_urls()]

    # -- pages -----------------------------------------------------------------------------
    def each_context(self, request: HttpRequest) -> dict[str, Any]:
        context: dict[str, Any] = super().each_context(request)
        context["mfa_reminder"] = getattr(request, "mfa_reminder", None)
        context["portal_url"] = reverse("portal:dashboard")
        return context
