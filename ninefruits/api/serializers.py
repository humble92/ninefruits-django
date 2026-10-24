"""API serializers. Credentials, personal identifiers and token digests never appear here."""

from __future__ import annotations

from typing import Any

from rest_framework import serializers

from ninefruits.lms.actions.deliver import FINAL_STATUSES, REPORTABLE
from ninefruits.lms.models import LmsCourseLink, LmsPlatform


class PlatformSerializer(serializers.ModelSerializer):  # type: ignore[type-arg]
    name = serializers.SerializerMethodField()

    class Meta:
        model = LmsPlatform
        fields = ("code", "name", "driver", "base_url", "is_active", "should_sync_enrollments", "should_pull_grades")

    def get_name(self, obj: LmsPlatform) -> dict[str, str]:
        return obj.name_translations


class CourseLinkSerializer(serializers.ModelSerializer):  # type: ignore[type-arg]
    platform = serializers.CharField(source="platform.code")
    term = serializers.CharField(source="section.term.code")
    section = serializers.SerializerMethodField()

    class Meta:
        model = LmsCourseLink
        fields = (
            "platform",
            "section_id",
            "section",
            "term",
            "external_course_id",
            "external_url",
            "status",
            "last_synced_at",
            "last_error",
        )

    def get_section(self, obj: LmsCourseLink) -> str:
        return obj.section.label()


class SyncResultSerializer(serializers.Serializer):  # type: ignore[type-arg]
    """The outcome of a step the platform processed."""

    log_id = serializers.IntegerField(required=False, min_value=1, help_text="A queued sync log entry to finish")
    operation = serializers.ChoiceField(choices=[str(value) for value in REPORTABLE])
    status = serializers.ChoiceField(choices=[str(value) for value in FINAL_STATUSES])
    message = serializers.CharField(required=False, allow_blank=True, max_length=1000)
    section_id = serializers.IntegerField(required=False, min_value=1)
    external_course_id = serializers.CharField(required=False, max_length=128)
    external_url = serializers.URLField(required=False, max_length=512)


class ScoreDeliverySerializer(serializers.Serializer):  # type: ignore[type-arg]
    """A course's final scores: external user id -> score (0-100)."""

    external_course_id = serializers.CharField(max_length=128)
    scores = serializers.DictField(child=serializers.FloatField(min_value=0, max_value=100), allow_empty=False)

    def validate_scores(self, value: dict[str, Any]) -> dict[str, Any]:
        if len(value) > 5000:
            raise serializers.ValidationError("At most 5000 scores per delivery.")
        return value


class TokenRequestSerializer(serializers.Serializer):  # type: ignore[type-arg]
    days = serializers.IntegerField(required=False, min_value=1, max_value=365)
    note = serializers.CharField(required=False, allow_blank=True, max_length=200)
