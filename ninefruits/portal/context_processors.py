"""Template context shared by the portal and guest layouts."""

from __future__ import annotations

from django.http import HttpRequest
from django.utils.functional import SimpleLazyObject


def site(request: HttpRequest) -> dict[str, object]:
    """``site_name``: the institution name in the current language (original ``brandName``)."""
    from ninefruits.adminpanel.config import institution_name

    return {"site_name": SimpleLazyObject(institution_name)}
