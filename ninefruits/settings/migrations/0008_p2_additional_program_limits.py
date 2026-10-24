"""Original database/settings/2026_10_22_004410_add_additional_program_limits (settings group
``student_records``; the first two values came with 0005_authentication_settings)."""

from django.db import migrations

from ninefruits.settings.groups.base import add_settings, delete_settings


def forwards(apps, schema_editor):  # type: ignore[no-untyped-def]
    add_settings(apps, "student_records", {"max_second_majors": 1, "max_minors": 1})


def backwards(apps, schema_editor):  # type: ignore[no-untyped-def]
    delete_settings(apps, "student_records", ["max_second_majors", "max_minors"])


class Migration(migrations.Migration):
    dependencies = [("appsettings", "0007_merge_institution_security")]

    operations = [migrations.RunPython(forwards, backwards)]
