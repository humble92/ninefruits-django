from django.db import models

from ninefruits.core.models import TimeStampedModel


class SettingValue(TimeStampedModel):
    """One row of the original spatie/laravel-settings ``settings`` table."""

    group = models.CharField(max_length=255)
    name = models.CharField(max_length=255)
    locked = models.BooleanField(default=False)
    payload = models.JSONField()

    class Meta:
        db_table = "settings"

    def __repr__(self) -> str:
        return f"<SettingValue {self.group}.{self.name}>"
