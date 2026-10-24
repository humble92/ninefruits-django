from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from .middleware import SESSION_KEY, supported_locales


@require_POST
def update_locale(request: HttpRequest) -> HttpResponse:
    locale = request.POST.get("locale", "")
    if locale in supported_locales():
        request.session[SESSION_KEY] = locale
        if request.user.is_authenticated:
            request.user.locale = locale  # type: ignore[union-attr]
            request.user.save(update_fields=["locale", "updated_at"])  # type: ignore[union-attr]
    target = request.POST.get("next") or request.headers.get("Referer") or "/"
    if not url_has_allowed_host_and_scheme(
        target, allowed_hosts={request.get_host()}, require_https=request.is_secure()
    ):
        target = "/"
    return redirect(target)
