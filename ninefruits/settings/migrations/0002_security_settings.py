"""Settings group ``security`` (original database/settings/2026_10_22_000110_create_security_settings)."""

from django.db import migrations

from ninefruits.settings.groups.base import add_settings


def forwards(apps, schema_editor):  # type: ignore[no-untyped-def]
    add_settings(
        apps,
        "security",
        {
            "mfa_enforcement": "recommended",
            "mfa_required_role_ids": [],
            "mfa_grace_period_days": 7,
            "mfa_remember_device_days": 30,
        },
    )


class Migration(migrations.Migration):
    dependencies = [("appsettings", "0001_initial")]

    operations = [migrations.RunPython(forwards, migrations.RunPython.noop)]
