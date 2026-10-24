"""Original database/settings/2026_10_23_004010_create_graduation_settings (settings group
``graduation``, ADR 0016): degree number pattern and the cumulative GPA required to graduate."""

from django.db import migrations

from ninefruits.settings.groups.base import add_settings, delete_settings

DEFAULTS = {
    # Tokens: {YYYY}/{YY} graduation year, {PROGRAM} program code, {SEQ:n} sequence per prefix.
    "degree_number_pattern": "{PROGRAM}-{YYYY}-{SEQ:5}",
    # Cumulative GPA required to graduate; null for none.
    "minimum_cumulative_gpa": 2.0,
}


def forwards(apps, schema_editor):  # type: ignore[no-untyped-def]
    add_settings(apps, "graduation", DEFAULTS)


def backwards(apps, schema_editor):  # type: ignore[no-untyped-def]
    delete_settings(apps, "graduation", list(DEFAULTS))


class Migration(migrations.Migration):
    dependencies = [("appsettings", "0014_p8_certificate_settings")]

    operations = [migrations.RunPython(forwards, backwards)]
