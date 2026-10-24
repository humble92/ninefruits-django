"""Original database/settings/2026_10_22_007210_raise_minimum_response_percent_setting: the
default minimum response rate is 25% (decided 2026-10-23); a value someone set is kept."""

from django.db import migrations

from ninefruits.settings.groups.base import update_setting


def forwards(apps, schema_editor):  # type: ignore[no-untyped-def]
    update_setting(
        apps, "evaluations", "minimum_response_percent", lambda percent: 25 if int(percent) == 0 else percent
    )


def backwards(apps, schema_editor):  # type: ignore[no-untyped-def]
    update_setting(
        apps, "evaluations", "minimum_response_percent", lambda percent: 0 if int(percent) == 25 else percent
    )


class Migration(migrations.Migration):
    dependencies = [("appsettings", "0012_p7_evaluation_settings")]

    operations = [migrations.RunPython(forwards, backwards)]
