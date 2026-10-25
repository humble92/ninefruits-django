"""Original database/settings/2026_10_23_004020_graduation_defaults: decided 2026-10-23, a 2.0
cumulative GPA to graduate and degree numbers per program and year."""

from django.db import migrations

from ninefruits.settings.groups.base import json_payload, update_setting


def forwards(apps, schema_editor):  # type: ignore[no-untyped-def]
    update_setting(apps, "graduation", "minimum_cumulative_gpa", lambda gpa: 2.0)
    update_setting(apps, "graduation", "degree_number_pattern", lambda pattern: "{PROGRAM}-{YYYY}-{SEQ:5}")


def backwards(apps, schema_editor):  # type: ignore[no-untyped-def]
    update_setting(apps, "graduation", "minimum_cumulative_gpa", lambda gpa: json_payload(None))
    update_setting(apps, "graduation", "degree_number_pattern", lambda pattern: "{YYYY}-{SEQ:5}")


class Migration(migrations.Migration):
    dependencies = [("appsettings", "0015_p11_graduation_settings")]

    operations = [migrations.RunPython(forwards, backwards)]
