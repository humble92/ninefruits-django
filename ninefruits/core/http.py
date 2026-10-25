"""Request helpers shared by the middleware, rate limits and audit."""

from __future__ import annotations

import ipaddress

from django.conf import settings
from django.http import HttpRequest


def client_ip(request: HttpRequest) -> str:
    """The client's IP address.

    Without proxies (``TRUSTED_PROXY_COUNT = 0``) this is ``REMOTE_ADDR``. Behind
    ``TRUSTED_PROXY_COUNT`` reverse proxies that append to ``X-Forwarded-For`` (Nginx
    ``proxy_add_x_forwarded_for``), it is the address the outermost trusted proxy saw: the
    entry counted from the right. Entries further left are client supplied and never trusted.
    A malformed or too short header falls back to ``REMOTE_ADDR``."""
    remote = str(request.META.get("REMOTE_ADDR") or "")
    count = int(getattr(settings, "TRUSTED_PROXY_COUNT", 0))
    forwarded = str(request.META.get("HTTP_X_FORWARDED_FOR") or "")
    if count <= 0 or not forwarded:
        return remote
    hops = [hop.strip() for hop in forwarded.split(",")]
    if len(hops) < count:
        return remote
    try:
        return str(ipaddress.ip_address(hops[-count]))
    except ValueError:
        return remote
