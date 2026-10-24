"""Original database/settings/2026_10_23_000110_add_relative_grade_caps: grade caps for relative
evaluation (decided 2026-10-23). A at most 30%, B at most 40% of a section's graded students,
1 percent point of tolerance, sections under 10 students exempt."""

from django.db import migrations

from ninefruits.settings.groups.base import add_settings, delete_settings

DEFAULTS = {
    "relative_grade_caps": {"A": 30, "B": 40},
    "relative_cap_tolerance_percent": 1,
    "relative_minimum_students": 10,
}


def forwards(apps, schema_editor):  # type: ignore[no-untyped-def]
    add_settings(apps, "grading", DEFAULTS)


def backwards(apps, schema_editor):  # type: ignore[no-untyped-def]
    delete_settings(apps, "grading", list(DEFAULTS))


class Migration(migrations.Migration):
    dependencies = [("appsettings", "0010_p6_grading_settings")]

    operations = [migrations.RunPython(forwards, backwards)]
