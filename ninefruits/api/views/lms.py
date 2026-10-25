"""LMS endpoints (porting-plan 12): what the platforms call back.

- ``GET /api/v1/lms/platforms/`` and ``/<code>/``: the platforms (never their credentials);
- ``GET /api/v1/lms/platforms/<code>/course-links/``: the platform's course links
  (``?term=<code>``, ``?status=linked``);
- ``POST /api/v1/lms/platforms/<code>/sync-results/``: the outcome of a step the platform
  processed (``RecordPlatformCallback.sync_result``);
- ``POST /api/v1/lms/platforms/<code>/scores/``: final scores for a course, kept as a draft for
  the grade entry screen (``RecordPlatformCallback.deliver_scores``).

Every endpoint needs ``lms.manage`` (an integration token of a service account)."""

from __future__ import annotations

from typing import Any

from django.core.exceptions import ValidationError as DjangoValidationError
from drf_spectacular.utils import OpenApiParameter, extend_schema, inline_serializer
from rest_framework import serializers, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.request import Request
from rest_framework.response import Response

from ninefruits.api.pagination import LimitOffsetPagination
from ninefruits.api.permissions import HasCatalogPermission
from ninefruits.api.serializers import (
    CourseLinkSerializer,
    PlatformSerializer,
    ScoreDeliverySerializer,
    SyncResultSerializer,
)
from ninefruits.lms.actions import RecordPlatformCallback
from ninefruits.lms.enums import LinkStatus
from ninefruits.lms.models import LmsCourseLink, LmsPlatform
from ninefruits.security.enums import Permission


def _drf_error(error: DjangoValidationError) -> ValidationError:
    if hasattr(error, "error_dict"):
        return ValidationError(error.message_dict)
    return ValidationError({"detail": error.messages})


class PlatformViewSet(viewsets.ReadOnlyModelViewSet):  # type: ignore[type-arg]
    serializer_class = PlatformSerializer
    permission_classes = [HasCatalogPermission(Permission.LMS_MANAGE)]  # type: ignore[list-item]  # an instance (HasCatalogPermission.__call__)
    lookup_field = "code"
    lookup_value_regex = r"[A-Za-z0-9_-]+"
    pagination_class = None

    def get_queryset(self) -> Any:
        return LmsPlatform.objects.visible_to(self.request.user).order_by("code")

    @extend_schema(
        responses=CourseLinkSerializer(many=True),
        parameters=[
            OpenApiParameter("term", str, description="Term code"),
            OpenApiParameter("status", str, enum=[str(value) for value in LinkStatus.values]),
        ],
    )
    @action(detail=True, methods=["get"], url_path="course-links")
    def course_links(self, request: Request, code: str | None = None) -> Response:
        platform = self.get_object()
        links = (
            LmsCourseLink.objects.visible_to(request.user)
            .filter(platform=platform)
            .select_related("platform", "section__course", "section__term")
            .order_by("section_id")
        )
        if request.query_params.get("term"):
            links = links.filter(section__term__code=request.query_params["term"])
        if request.query_params.get("status"):
            links = links.filter(status=request.query_params["status"])
        paginator = LimitOffsetPagination()
        page = paginator.paginate_queryset(links, request, view=self)
        return paginator.get_paginated_response(CourseLinkSerializer(page, many=True).data)

    @extend_schema(
        request=SyncResultSerializer,
        responses={
            201: inline_serializer(
                "SyncResultRecorded", {"log_id": serializers.IntegerField(), "status": serializers.CharField()}
            )
        },
    )
    @action(detail=True, methods=["post"], url_path="sync-results")
    def sync_results(self, request: Request, code: str | None = None) -> Response:
        platform = self.get_object()
        data = SyncResultSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        try:
            log = RecordPlatformCallback().sync_result(platform, request.user, **data.validated_data)
        except DjangoValidationError as error:
            raise _drf_error(error) from error
        return Response({"log_id": log.pk, "status": log.status}, status=status.HTTP_201_CREATED)

    @extend_schema(
        request=ScoreDeliverySerializer,
        responses={
            201: inline_serializer(
                "ScoresDelivered",
                {
                    "section_id": serializers.IntegerField(),
                    "scores": serializers.IntegerField(),
                    "matched": serializers.IntegerField(),
                },
            )
        },
    )
    @action(detail=True, methods=["post"], url_path="scores")
    def scores(self, request: Request, code: str | None = None) -> Response:
        platform = self.get_object()
        data = ScoreDeliverySerializer(data=request.data)
        data.is_valid(raise_exception=True)
        try:
            result = RecordPlatformCallback().deliver_scores(platform, request.user, **data.validated_data)
        except DjangoValidationError as error:
            raise _drf_error(error) from error
        return Response(result, status=status.HTTP_201_CREATED)
