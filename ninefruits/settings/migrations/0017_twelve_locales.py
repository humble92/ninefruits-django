"""Twelve languages ship with the application from 2026-11-11 (German, Russian, Malay, Filipino,
French, Japanese, Mongolian, Nepali, Thai, Turkish, Uzbek, Vietnamese): they join the default list
of supported locales (original database/settings/2026_11_11_000010_add_twelve_locales).
Installations that changed the list on purpose keep it and enable the new languages in the
institution settings."""

from django.db import migrations

from ninefruits.settings.groups.base import update_setting

SHIPPED_DEFAULT = {"en", "ko", "zh-hans", "lo"}
ADDED = ["de", "ru", "ms", "fil", "fr", "ja", "mn", "ne", "th", "tr", "uz", "vi"]


def forwards(apps, schema_editor):  # type: ignore[no-untyped-def]
    update_setting(
        apps,
        "institution",
        "supported_locales",
        lambda locales: [*locales, *ADDED] if set(locales) == SHIPPED_DEFAULT else locales,
    )


def backwards(apps, schema_editor):  # type: ignore[no-untyped-def]
    update_setting(apps, "institution", "supported_locales", lambda locales: [c for c in locales if c not in ADDED])


class Migration(migrations.Migration):
    dependencies = [("appsettings", "0016_p11_graduation_defaults")]

    operations = [migrations.RunPython(forwards, backwards)]
