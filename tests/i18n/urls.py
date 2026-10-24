"""Test-only URLs: the project's URLs plus views that show the request's locale."""

from django.http import HttpRequest, HttpResponse, JsonResponse
from django.urls import include, path
from django.utils import translation
from django.utils.translation import pgettext

from config.urls import urlpatterns as project_urlpatterns
from ninefruits.core.db import session_context


def language_view(request: HttpRequest) -> HttpResponse:
    return HttpResponse(f"{translation.get_language()}|{pgettext('common', 'Language')}")


def database_context_view(request: HttpRequest) -> JsonResponse:
    return JsonResponse(session_context().current())


urlpatterns = [
    path("_test/language/", language_view),
    path("_test/database-context/", database_context_view),
    path("", include(project_urlpatterns)),
]
