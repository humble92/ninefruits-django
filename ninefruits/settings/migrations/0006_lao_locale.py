"""Lao (``lo``) ships with the application from 2026-10-23: it joins the default list of supported
locales (original database/settings/2026_10_23_008010_add_lao_locale). Installations that
changed the list on purpose keep it."""

from django.db import migrations

from ninefruits.settings.groups.base import update_setting

SHIPPED_DEFAULT = {"en", "ko", "zh-hans"}


def forwards(apps, schema_editor):  # type: ignore[no-untyped-def]
    update_setting(
        apps,
        "institution",
        "supported_locales",
        lambda locales: [*locales, "lo"] if set(locales) == SHIPPED_DEFAULT else locales,
    )


def backwards(apps, schema_editor):  # type: ignore[no-untyped-def]
    update_setting(apps, "institution", "supported_locales", lambda locales: [c for c in locales if c != "lo"])


class Migration(migrations.Migration):
    dependencies = [("appsettings", "0004_institution_settings")]

    operations = [migrations.RunPython(forwards, backwards)]
