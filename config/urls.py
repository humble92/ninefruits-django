from django.conf import settings
from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("accounts/", include("ninefruits.security.urls")),
    path("accounts/", include("allauth.urls")),
    path("auth/sso/", include("ninefruits.security.sso_urls")),
    path("i18n/", include("ninefruits.i18n.urls")),
    path("portal/", include("ninefruits.portal.urls")),
    path("", include("ninefruits.person.urls")),
    path("", include("ninefruits.admission.urls")),
    path("", include("ninefruits.grading.urls")),
    path("", include("ninefruits.certificate.urls")),
    path("", include("ninefruits.assessment.urls")),
    path("", include("ninefruits.attendance.urls")),
    path("", include("ninefruits.core.urls")),
]

if settings.DEBUG and "debug_toolbar" in settings.INSTALLED_APPS:  # pragma: no cover
    urlpatterns.append(path("__debug__/", include("debug_toolbar.urls")))
