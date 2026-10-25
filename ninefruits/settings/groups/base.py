"""Settings groups (original spatie/laravel-settings classes, porting-plan 5.1).

A group is a pydantic model whose fields are the settings of one group in the ``settings``
table (one row per field, ``payload`` is the JSON value)::

    class SecuritySettings(SettingsGroup):
        group: ClassVar[str] = "security"
        mfa_enforcement: MfaEnforcement
        mfa_grace_period_days: int

    settings = SecuritySettings.load()      # cached per request/task, see invalidate()
    settings.mfa_grace_period_days = 14
    settings.save(reason="...")             # validates, writes, audits

Defaults are not declared on the class: values come from the data migrations, as in the
original. ``load()`` raises ``MissingSettings`` when a row is missing.
"""

from __future__ import annotations

from typing import Any, ClassVar, Self

from django.core.cache import cache
from django.db import transaction
from pydantic import BaseModel, ConfigDict

CACHE_PREFIX = "settings:group:"


class MissingSettings(LookupError):
    pass


def json_payload(value: Any) -> Any:
    """``None`` is stored as JSON ``null`` (the column is ``NOT NULL``), like the original."""
    from django.db.models import JSONNull

    return JSONNull() if value is None else value


class SettingsGroup(BaseModel):
    model_config = ConfigDict(validate_assignment=True, use_enum_values=False)

    group: ClassVar[str]
    registry: ClassVar[dict[str, type[SettingsGroup]]] = {}

    def __init_subclass__(cls, **kwargs: Any) -> None:
        super().__init_subclass__(**kwargs)
        if "group" in cls.__dict__:
            SettingsGroup.registry[cls.group] = cls

    @classmethod
    def load(cls) -> Self:
        cached = cache.get(CACHE_PREFIX + cls.group)
        if cached is not None:
            return cls.model_validate(cached)
        from ninefruits.settings.models import SettingValue

        rows = {row.name: row.payload for row in SettingValue.objects.filter(group=cls.group)}
        missing = [name for name in cls.model_fields if name not in rows]
        if missing:
            raise MissingSettings(f"Settings {cls.group}.{', '.join(missing)} are missing; run migrate.")
        instance = cls.model_validate({name: rows[name] for name in cls.model_fields})
        cache.set(CACHE_PREFIX + cls.group, instance.model_dump(mode="json"), 60)
        return instance

    def save(self, *, reason: str | None = None) -> None:
        """Writes changed values. Callers record the business audit (``settings.updated``)."""
        from ninefruits.settings.models import SettingValue

        values = self.model_dump(mode="json")
        with transaction.atomic():
            for name, payload in values.items():
                SettingValue.objects.update_or_create(
                    group=self.group, name=name, defaults={"payload": json_payload(payload)}
                )
        type(self).invalidate()

    @classmethod
    def invalidate(cls) -> None:
        cache.delete(CACHE_PREFIX + cls.group)


def add_settings(apps: Any, group: str, values: dict[str, Any]) -> None:
    """For ``RunPython`` data migrations (original ``$this->migrator->add``). Existing rows are
    kept, so installations keep their changes."""
    SettingValue = apps.get_model("appsettings", "SettingValue")
    for name, payload in values.items():
        SettingValue.objects.get_or_create(
            group=group, name=name, defaults={"payload": json_payload(payload), "locked": False}
        )


def update_setting(apps: Any, group: str, name: str, update: Any) -> None:
    """Original ``$this->migrator->update``: ``update`` receives the current payload."""
    SettingValue = apps.get_model("appsettings", "SettingValue")
    row = SettingValue.objects.get(group=group, name=name)
    row.payload = update(row.payload)
    row.save(update_fields=["payload", "updated_at"])


def delete_settings(apps: Any, group: str, names: list[str]) -> None:
    SettingValue = apps.get_model("appsettings", "SettingValue")
    SettingValue.objects.filter(group=group, name__in=names).delete()
