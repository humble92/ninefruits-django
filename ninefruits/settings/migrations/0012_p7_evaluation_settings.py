"""Original database/settings/2026_10_22_007010_create_evaluation_settings (settings group
``evaluations``): course evaluation options (ADR 0012). Grades of a term stay hidden while its
evaluation is open and unfinished; uniform answers are accepted; a new term's evaluation shows
results from 5 responses. The minimum response rate starts at 0 and is raised to 25 by
``0013_p7_raise_minimum_response_percent``, as in the original."""

from django.db import migrations

from ninefruits.settings.groups.base import add_settings, delete_settings

DEFAULTS = {
    "grades_require_evaluation": True,
    "reject_uniform_answers": False,
    "minimum_responses": 5,
    "minimum_response_percent": 0,
}


def forwards(apps, schema_editor):  # type: ignore[no-untyped-def]
    add_settings(apps, "evaluations", DEFAULTS)


def backwards(apps, schema_editor):  # type: ignore[no-untyped-def]
    delete_settings(apps, "evaluations", list(DEFAULTS))


class Migration(migrations.Migration):
    dependencies = [("appsettings", "0011_p6_relative_grade_caps")]

    operations = [migrations.RunPython(forwards, backwards)]
