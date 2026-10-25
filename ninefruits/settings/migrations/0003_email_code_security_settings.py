"""Original database/settings/2026_10_22_000130_add_email_code_to_security_settings."""

from django.db import migrations

from ninefruits.settings.groups.base import add_settings


def forwards(apps, schema_editor):  # type: ignore[no-untyped-def]
    add_settings(apps, "security", {"mfa_email_code_enabled": False})


class Migration(migrations.Migration):
    dependencies = [("appsettings", "0002_security_settings")]

    operations = [migrations.RunPython(forwards, migrations.RunPython.noop)]
