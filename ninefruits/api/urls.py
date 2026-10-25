"""``/api/``: version 1 under ``/api/v1/`` (DRF router), the OpenAPI schema at ``/api/schema/``
(signed-in users) and Swagger UI at ``/api/docs/`` (``admin_panel.access``)."""

from __future__ import annotations

from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerSplitView
from rest_framework.permissions import IsAuthenticated
from rest_framework.routers import DefaultRouter

from ninefruits.api.permissions import HasCatalogPermission
from ninefruits.api.views.lms import PlatformViewSet
from ninefruits.api.views.reporting import ReportViewSet
from ninefruits.api.views.system import CertificateVerificationView, HealthView, MeView
from ninefruits.api.views.tokens import TokenDetailView, TokenListView
from ninefruits.security.enums import Permission

app_name = "api"

router = DefaultRouter()
router.include_root_view = False
router.register("lms/platforms", PlatformViewSet, basename="lms-platform")
router.register("reports", ReportViewSet, basename="report")

v1 = [
    path("health/", HealthView.as_view(), name="health"),
    path("me/", MeView.as_view(), name="me"),
    path("auth/tokens/", TokenListView.as_view(), name="tokens"),
    path("auth/tokens/<str:key>/", TokenDetailView.as_view(), name="token"),
    path("certificates/verify/<str:code>/", CertificateVerificationView.as_view(), name="certificate-verify"),
    *router.urls,
]

urlpatterns = [
    path("v1/", include(v1)),
    path("schema/", SpectacularAPIView.as_view(permission_classes=[IsAuthenticated]), name="schema"),
    path(
        "docs/",
        SpectacularSwaggerSplitView.as_view(
            url_name="api:schema", permission_classes=[HasCatalogPermission(Permission.ADMIN_PANEL_ACCESS)]
        ),
        name="docs",
    ),
]
