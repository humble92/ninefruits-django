"""Original database/settings/2026_10_22_003010_create_admission_settings (settings group
``admissions``)."""

from django.db import migrations

from ninefruits.settings.groups.base import add_settings, delete_settings

NAMES = ["applicant_registration_enabled", "draft_expiry_days", "max_document_size_mb"]


def forwards(apps, schema_editor):  # type: ignore[no-untyped-def]
    add_settings(
        apps,
        "admissions",
        {"applicant_registration_enabled": True, "draft_expiry_days": 90, "max_document_size_mb": 10},
    )


def backwards(apps, schema_editor):  # type: ignore[no-untyped-def]
    delete_settings(apps, "admissions", NAMES)


class Migration(migrations.Migration):
    dependencies = [("appsettings", "0008_p2_additional_program_limits")]

    operations = [migrations.RunPython(forwards, backwards)]
