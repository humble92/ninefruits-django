"""Settings group ``institution`` (original database/settings/2026_10_22_000120_create_institution_settings).
Locale codes are Django's: the original ``zh_CN`` is ``zh-hans``."""

from django.conf import settings
from django.db import migrations

from ninefruits.settings.groups.base import add_settings


def forwards(apps, schema_editor):  # type: ignore[no-untyped-def]
    add_settings(
        apps,
        "institution",
        {
            "name": {"en": settings.APP_NAME},
            "supported_locales": ["en", "ko", "zh-hans"],
            "default_locale": "en",
            "timezone": getattr(settings, "INSTITUTION_TIMEZONE", "UTC"),
        },
    )


class Migration(migrations.Migration):
    dependencies = [("appsettings", "0001_initial")]

    operations = [migrations.RunPython(forwards, migrations.RunPython.noop)]
