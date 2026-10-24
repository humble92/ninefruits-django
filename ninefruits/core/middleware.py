"""Request context and database session context middleware (original AssignRequestContext and
SetDatabaseSessionContext)."""

from __future__ import annotations

import re
import uuid
from collections.abc import Callable

from django.core.signals import request_finished
from django.http import HttpRequest, HttpResponse

from ninefruits.core import context
from ninefruits.core.db import session_context
from ninefruits.core.http import client_ip

_REQUEST_ID = re.compile(r"^[A-Za-z0-9._-]{8,64}$")


class AssignRequestContextMiddleware:
    """Request id (``X-Request-Id``), IP address and user agent for logs, tasks and audit."""

    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]) -> None:
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        request_id = request.headers.get("X-Request-Id", "")
        if not _REQUEST_ID.match(request_id):
            request_id = str(uuid.uuid4())
        request.request_id = request_id  # type: ignore[attr-defined]
        with context.bound(
            request_id=request_id,
            ip_address=client_ip(request),
            user_agent=request.headers.get("User-Agent", "")[:500],
            user_id=None,
            actor=None,
        ):
            response = self.get_response(request)
        response.headers["X-Request-Id"] = request_id
        return response


class SetDatabaseSessionContextMiddleware:
    """Passes the signed-in user to PostgreSQL (RLS, audit triggers) and clears it when the
    request ends, before the connection goes back to the pool."""

    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]) -> None:
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        user = getattr(request, "user", None)
        user_id = user.pk if user is not None and user.is_authenticated else None
        context.update(user_id=user_id, actor=f"user:{user_id}" if user_id else None)
        db_context = session_context()
        db_context.for_user(user_id, context.current().request_id)
        locale = getattr(request, "LANGUAGE_CODE", None)
        if locale:
            from django.conf import settings

            db_context.set_locale(locale, settings.FALLBACK_LANGUAGE)
        try:
            return self.get_response(request)
        finally:
            db_context.reset()


def _reset_on_request_finished(**kwargs: object) -> None:
    # Second guarantee (exceptions raised outside the middleware stack). Only touches the
    # database when something is set, so a closed connection is not reopened needlessly.
    db_context = session_context()
    if any(v for k, v in db_context.state.items() if db_context.baseline.get(k, "") != v):
        db_context.reset()


request_finished.connect(_reset_on_request_finished, dispatch_uid="ninefruits.core.reset_db_context")
