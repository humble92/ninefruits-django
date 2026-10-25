"""``{% sso_providers as providers %}``: enabled school sign-in providers for the sign-in page."""

from __future__ import annotations

from django import template

from ninefruits.security.services.sso import OidcProvider, enabled_providers

register = template.Library()


@register.simple_tag
def sso_providers() -> list[OidcProvider]:
    try:
        return enabled_providers()
    except Exception:
        return []
