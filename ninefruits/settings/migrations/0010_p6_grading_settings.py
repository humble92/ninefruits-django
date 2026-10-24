"""Original database/settings/2026_10_22_006010_create_grading_settings (settings group
``grading``): the grading policy. Defaults suit a Korean university; the legacy YUST profile sets
its own values."""

from django.db import migrations

from ninefruits.settings.groups.base import add_settings, delete_settings

DEFAULTS = {
    "gpa_decimals": 2,
    "gpa_rounding": "round",
    "retake_policy": "latest",
    "retake_max_grade": None,
    "standing_regular_terms_only": True,
    "warning_gpa_below": 1.75,
    "dismissal_warning_count": 0,
    "dismissal_consecutive_only": False,
    "honors_min_gpa": 4.0,
    "honors_min_credits": 15,
    "honors_exclude_failing": True,
}


def forwards(apps, schema_editor):  # type: ignore[no-untyped-def]
    add_settings(apps, "grading", DEFAULTS)


def backwards(apps, schema_editor):  # type: ignore[no-untyped-def]
    delete_settings(apps, "grading", list(DEFAULTS))


class Migration(migrations.Migration):
    dependencies = [("appsettings", "0009_p3_admission_settings")]

    operations = [migrations.RunPython(forwards, backwards)]
