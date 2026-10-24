"""Locale switcher (original ``UpdateLocaleController``, route ``locale.update``).

``POST locale=<code>`` (``language=<code>`` is accepted too: the admin language menu posts it).
The choice is stored in the session and, for signed-in users, in ``users.locale``. A language the
institution does not offer is rejected with a validation message, then the user goes back.
The original route had no rate limit; neither has this one.
"""

from __future__ import annotations

from django import forms
from django.contrib import messages
from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect
from django.utils.http import url_has_allowed_host_and_scheme
from django.utils.translation import pgettext_lazy
from django.views.decorators.http import require_POST

from ninefruits.institution.services.supported_locales import SupportedLocales

from .middleware import SESSION_KEY


class LocaleForm(forms.Form):
    locale = forms.ChoiceField(label=pgettext_lazy("common", "Language"))

    def __init__(self, *args: object, **kwargs: object) -> None:
        super().__init__(*args, **kwargs)  # type: ignore[arg-type]
        self.fields["locale"].choices = SupportedLocales().choices()  # type: ignore[attr-defined]


def _back(request: HttpRequest) -> HttpResponse:
    target = request.POST.get("next") or request.headers.get("Referer") or "/"
    if not url_has_allowed_host_and_scheme(
        target, allowed_hosts={request.get_host()}, require_https=request.is_secure()
    ):
        target = "/"
    return redirect(target)


@require_POST
def update_locale(request: HttpRequest) -> HttpResponse:
    data = {"locale": request.POST.get("locale") or request.POST.get("language") or ""}
    form = LocaleForm(data)
    if not form.is_valid():
        for error in form.errors.get("locale", []):
            messages.error(request, str(error))
        return _back(request)
    locale = form.cleaned_data["locale"]
    request.session[SESSION_KEY] = locale
    user = request.user
    if user.is_authenticated:
        user.locale = locale
        user.save(update_fields=["locale", "updated_at"])
    return _back(request)
