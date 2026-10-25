"""Settings group ``authentication`` (original
database/settings/2026_10_22_002010_create_authentication_settings). The original migration also
adds two ``student_records`` settings; they are kept here so the rows match. Their settings group
class arrives with the person app (Phase 2)."""

from django.db import migrations

from ninefruits.settings.groups.base import add_settings


def forwards(apps, schema_editor):  # type: ignore[no-untyped-def]
    add_settings(
        apps,
        "authentication",
        {
            "student_number_login": "disabled",
            "password_login_for_sso_users": True,
            "sso_link_mode": "manual",
            "sso_providers": [],
            "lockout_threshold": 10,
            "lockout_minutes": 15,
        },
    )
    add_settings(
        apps,
        "student_records",
        {
            "student_number_pattern": "{YYYY}{SEQ:5}",
            "invitation_valid_days": 14,
        },
    )


class Migration(migrations.Migration):
    dependencies = [("appsettings", "0003_email_code_security_settings")]

    operations = [migrations.RunPython(forwards, migrations.RunPython.noop)]
