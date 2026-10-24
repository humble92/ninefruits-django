"""Portal home (original ``App\\Livewire\\Portal\\Dashboard``)."""

from __future__ import annotations

from typing import Any

from django.contrib.auth.mixins import LoginRequiredMixin
from django.utils.translation import pgettext
from django.views.generic import TemplateView

from ninefruits.portal.access import active_role_names, persona_label, personas_for
from ninefruits.security.enums import Permission


class DashboardView(LoginRequiredMixin, TemplateView):
    template_name = "portal/dashboard.html"

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)
        user = self.request.user
        context.update(
            {
                "title": pgettext("portal", "Home"),
                "display_name": str(user),
                "roles": active_role_names(self.request),
                "personas": [persona_label(persona) for persona in personas_for(self.request)],
                "can_access_admin": user.has_perm(Permission.ADMIN_PANEL_ACCESS),
            }
        )
        return context
