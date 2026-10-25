"""Original database/settings/2026_10_23_001010_create_certificate_settings (settings group
``certificates``, ADR 0013): serial number pattern, verification period, default signers."""

from django.db import migrations

from ninefruits.settings.groups.base import add_settings, delete_settings

DEFAULTS = {
    # Tokens: {TYPE} type code, {YYYY}/{YY} issue year, {SEQ:n} sequence per prefix.
    "serial_pattern": "{TYPE}-{YYYY}-{SEQ:6}",
    # Days the verification page confirms an issue; 0 for no limit.
    "verification_valid_days": 0,
    "signer": {},
}


def forwards(apps, schema_editor):  # type: ignore[no-untyped-def]
    add_settings(apps, "certificates", DEFAULTS)


def backwards(apps, schema_editor):  # type: ignore[no-untyped-def]
    delete_settings(apps, "certificates", list(DEFAULTS))


class Migration(migrations.Migration):
    dependencies = [("appsettings", "0013_p7_raise_minimum_response_percent")]

    operations = [migrations.RunPython(forwards, backwards)]
